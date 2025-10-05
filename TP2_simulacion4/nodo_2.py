# nodo_2.py 
from flask import Flask, request, render_template_string, redirect, url_for, jsonify
from datetime import datetime
import json
import requests

app = Flask(__name__)

# ⚙️ Cambiá estos datos según el nodo:
NODE_NAME = "NODO 2 - Córdoba"
PORT = 5002
COLOR = "#7fb7ff"  # azul


# lista de los otros nodos
OTHER_NODES = [
    "http://127.0.0.1:5001",
    "http://127.0.0.1:5002",
    "http://127.0.0.1:5003"
]
OTHER_NODES.remove(f"http://127.0.0.1:{PORT}")

# base local de productos
products = {}
sessions = {}

# HTML con login y panel
HTML = """
<!doctype html>
<html>
<head>
<meta charset="utf-8">
<title>{{node_name}}</title>
<style>
body {background:#000;color:#ddd;font-family:monospace;padding:20px;}
h1 {color:{{color}};}
input,button {padding:6px;margin:4px;}
pre {background:#111;padding:10px;border-radius:8px;}
a.btn {background:{{color}};color:#000;padding:5px 10px;border-radius:5px;text-decoration:none;}
</style>
</head>
<body>
<h1>{{node_name}}</h1>
<p>Puerto: {{port}} — Última actualización: {{now}}</p>

{% if not session_user %}
<form method="post" action="/login">
  <input name="username" placeholder="Usuario" required>
  <button type="submit">Ingresar</button>
</form>
{% else %}
<p>🟢 Sesión activa: <b>{{session_user}}</b> (<a href="/logout">cerrar</a>)</p>
<form method="post" action="/write">
  <input name="product_id" placeholder="ID producto" required>
  <input name="name" placeholder="Nombre producto">
  <input name="stock" placeholder="Stock" type="number">
  <input name="price" placeholder="Precio" type="number">
  <input name="location" placeholder="Ubicación">
  <button type="submit">WRITE</button>
</form>

<form method="get" action="/read">
  <input name="product_id" placeholder="ID producto" required>
  <button type="submit">READ</button>
</form>

<a class="btn" href="/sync">🔄 Sincronizar nodos</a>
{% endif %}

<h2>Productos almacenados</h2>
<pre>{{products_pretty}}</pre>

</body>
</html>
"""

def now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

@app.route("/", methods=["GET"])
def index():
    user = sessions.get("active_user")
    return render_template_string(HTML, node_name=NODE_NAME, color=COLOR, port=PORT,
                                  now=now_str(), products_pretty=json.dumps(products, indent=2, ensure_ascii=False),
                                  session_user=user)

@app.route("/login", methods=["POST"])
def login():
    username = request.form["username"]
    sessions["active_user"] = username
    print(f"🟢 Nueva sesión iniciada: {username}")
    return redirect(url_for("index"))

@app.route("/logout")
def logout():
    sessions["active_user"] = None
    return redirect(url_for("index"))

@app.route("/read", methods=["GET"])
def read():
    pid = request.args.get("product_id")
    user = sessions.get("active_user", "anon")
    product = products.get(pid)
    print(f"[{user}] READ {pid} -> {product}")
    return redirect(url_for("index"))

@app.route("/write", methods=["POST"])
def write():
    pid = request.form["product_id"]
    user = sessions.get("active_user", "anon")
    payload = {
        "name": request.form.get("name", ""),
        "stock": int(request.form.get("stock") or 0),
        "price": float(request.form.get("price") or 0),
        "location": request.form.get("location", ""),
        "last_updated": datetime.now().timestamp()
    }
    products[pid] = payload
    print(f"[{user}] WRITE {pid} -> {payload}")
    return redirect(url_for("index"))

@app.route("/api", methods=["GET"])
def api():
    return jsonify(products)

@app.route("/sync", methods=["GET"])
def sync_all():
    for node in OTHER_NODES:
        try:
            resp = requests.get(f"{node}/api", timeout=3)
            data = resp.json()
            merged = 0
            for pid, pdata in data.items():
                incoming_ts = pdata.get("last_updated", 0)
                existing = products.get(pid)
                if (not existing) or (incoming_ts > existing.get("last_updated", 0)):
                    products[pid] = pdata
                    merged += 1
            print(f"🔁 Sync con {node} completado (merged={merged})")
        except Exception as e:
            print(f"⚠️ No se pudo sincronizar con {node}: {e}")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=PORT, debug=True)
