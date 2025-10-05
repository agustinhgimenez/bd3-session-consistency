# nodes/nodo_2.py
from flask import Flask, request, render_template, redirect, url_for, jsonify
from datetime import datetime
import json
import requests

app = Flask(__name__)

NODE_NAME = "NODO 2 - Córdoba"
COLOR = "#7fb7ff"
PORT = 5002

OTHER_NODES = [
    "http://127.0.0.1:5001",
    "http://127.0.0.1:5002",
    "http://127.0.0.1:5003",
]
OTHER_NODES.remove(f"http://127.0.0.1:{PORT}")

products = {}
sessions = {}
ops_log = []

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def ensure_session(session_id: str):
    if session_id not in sessions:
        sessions[session_id] = {"token": {}}
    return sessions[session_id]["token"]

def local_version(pid: str) -> int:
    return products.get(pid, {}).get("version", 0)

def merge_product(pid: str, pdata: dict) -> bool:
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
        "type": op_type,
        "key": key,
        "value": value,
        "timestamp": datetime.now().isoformat(),
        "session_id": session_id
    })

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

    needed = token.get(pid, 0)
    tries = 0
    while local_version(pid) < needed and tries < 2:
        _sync_internal()
        tries += 1

    token[pid] = max(token.get(pid, 0), local_version(pid))
    record_op("read", pid, session_id)

    print(f"[{session_id}] READ {pid} -> v{local_version(pid)} data={products.get(pid)}")
    return redirect(url_for("index"))

@app.route("/write", methods=["POST"])
def write():
    pid = request.form["product_id"].strip()
    session_id = sessions.get("active_user", "anon")
    token = ensure_session(session_id)

    for dep_pid, min_v in token.items():
        tries = 0
        while local_version(dep_pid) < min_v and tries < 2:
            _sync_internal()
            tries += 1

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

    token[pid] = max(token.get(pid, 0), new_version)
    record_op("write", pid, session_id, value=payload)

    print(f"[{session_id}] WRITE {pid} -> v{new_version} {payload}")
    return redirect(url_for("index"))

@app.route("/api", methods=["GET"])
def api():
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
