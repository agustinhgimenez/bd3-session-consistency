# nodes/nodo_1.py
from flask import Flask, request, render_template, redirect, url_for, jsonify
from datetime import datetime
import json
import requests
import os  # <--- NUEVO

# Ruta absoluta a ../templates (carpeta hermana de nodes/)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "..", "templates")

app = Flask(__name__, template_folder=TEMPLATES_DIR)  # <--- CAMBIADO

# ⚙️ Datos del nodo
NODE_NAME = "NODO 1 - Rosario"
COLOR = "#57ff8a"
PORT = 5001

# Peers (quitarme a mí mismo)
OTHER_NODES = [
    "http://127.0.0.1:5001",
    "http://127.0.0.1:5002",
    "http://127.0.0.1:5003",
]
OTHER_NODES.remove(f"http://127.0.0.1:{PORT}")

# ====== Estado ======
# productos: pid -> {name, stock, price, location, last_updated, version}
products = {}
# sesiones: session_id -> {"token": {pid: min_version_vista}}
sessions = {}          # y sessions["active_user"] para la UI
ops_log = []           # registro de operaciones (READ/WRITE)

# ====== Helpers ======
def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def ensure_session(session_id: str):
    if session_id not in sessions:
        sessions[session_id] = {"token": {}}
    return sessions[session_id]["token"]

def local_version(pid: str) -> int:
    return products.get(pid, {}).get("version", 0)

def merge_product(pid: str, pdata: dict) -> bool:
    """Merge por versión. Empate por last_updated. Devuelve True si modificó."""
    incoming_v = pdata.get("version", 0)
    local_v = local_version(pid)
    if incoming_v > local_v:
        products[pid] = pdata
        return True
    if incoming_v == local_v:
        if pdata.get("last_updated", 0) > products.get(pid, {}).get("last_updated", 0):
            products[pid] = pdata
            return True
    return False

def _sync_internal():
    merged_total = 0
    for node in OTHER_NODES:
        try:
            resp = requests.get(f"{node}/api", timeout=3)
            data = resp.json()
            for pid, pdata in data.items():
                if merge_product(pid, pdata):
                    merged_total += 1
        except Exception as e:
            print(f"⚠️ Sync falló con {node}: {e}")
    if merged_total:
        print(f"🔁 Sync merged={merged_total}")

def record_op(op_type: str, key: str, session_id: str, value=None):
    ops_log.append({
        "type": op_type,                    # "read" | "write"
        "key": key,
        "value": value,                     # dict del write o None en read
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id
    })

# ====== Rutas ======
@app.route("/", methods=["GET"])
def index():
    user = sessions.get("active_user")
    token = sessions.get(user, {}).get("token", {}) if user else {}
    return render_template(
        "panel.html",
        node_name=NODE_NAME, color=COLOR, port=PORT,
        now=now_str(),
        products_pretty=json.dumps(products, indent=2, ensure_ascii=False),
        session_user=user,
        session_token_pretty=json.dumps(token, indent=2, ensure_ascii=False)
    )

@app.route("/login", methods=["POST"])
def login():
    session_id = request.form["username"].strip()
    sessions["active_user"] = session_id
    ensure_session(session_id)
    print(f"🟢 Nueva sesión: {session_id}")
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    sessions["active_user"] = None
    return redirect(url_for("index"))

@app.route("/read", methods=["GET"])
def read():
    pid = request.args.get("product_id", "").strip()
    session_id = sessions.get("active_user", "anon")
    token = ensure_session(session_id)

    # RYW/MR: ver al menos token[pid]
    needed = token.get(pid, 0)
    tries = 0
    while local_version(pid) < needed and tries < 2:
        _sync_internal()
        tries += 1

    # actualizar token con la versión efectivamente vista
    token[pid] = max(token.get(pid, 0), local_version(pid))
    record_op("read", pid, session_id)

    print(f"[{session_id}] READ {pid} -> v{local_version(pid)} data={products.get(pid)}")
    return redirect(url_for("index"))

@app.route("/write", methods=["POST"])
def write():
    pid = request.form["product_id"].strip()
    session_id = sessions.get("active_user", "anon")
    token = ensure_session(session_id)

    # WFR: asegurar dependencias del token
    for dep_pid, min_v in token.items():
        tries = 0
        while local_version(dep_pid) < min_v and tries < 2:
            _sync_internal()
            tries += 1

    # aplicar write local: incrementa version
    new_version = local_version(pid) + 1
    payload = {
        "name": request.form.get("name", ""),
        "stock": int(request.form.get("stock") or 0),
        "price": float(request.form.get("price") or 0),
        "location": request.form.get("location", ""),
        "last_updated": datetime.now().timestamp(),
        "version": new_version
    }
    products[pid] = payload

    # RYW: la sesión ve al menos esta versión
    token[pid] = max(token.get(pid, 0), new_version)
    record_op("write", pid, session_id, value=payload)

    print(f"[{session_id}] WRITE {pid} -> v{new_version} {payload}")
    return redirect(url_for("index"))

@app.route("/api", methods=["GET"])
def api():
    # asegurar que todo tenga version (por si quedara algo viejo)
    for pid, pdata in list(products.items()):
        if "version" not in pdata:
            pdata["version"] = 1
    return jsonify(products)

@app.route("/sync", methods=["GET"])
def sync_all():
    _sync_internal()
    return redirect(url_for("index"))

@app.route("/ops", methods=["GET"])
def ops():
    return jsonify({"node": NODE_NAME, "ops": ops_log})

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT, debug=True)
