# TP2 – Consistencia Causal desde la Perspectiva del Cliente (Garantías de Sesión)

📚 **Materia:** Bases de Datos III – FIE (UNDEF)  
👥 **Equipo 2**  
💻 **Stack:** Python 3.11, Flask, Requests

---

## 🎯 Objetivo
Implementar un sistema distribuido simulado con **consistencia causal desde la perspectiva del cliente**, utilizando **garantías de sesión**:
- **Read-Your-Writes (RYW)**
- **Monotonic Reads (MR)**
- **Writes-Follow-Reads (WFR)**

Cada usuario mantiene una sesión con un **token** `{clave → versión vista}`, garantizando que sus lecturas y escrituras se ejecuten en el orden correcto.

---

## ⚙️ Estructura
```
.
├─ nodes/              # los 3 nodos Flask
├─ templates/          # panel HTML del sistema
├─ scripts/            # script para correr los tres nodos
├─ requirements.txt
├─ .gitignore
└─ README.md
```

---

## 🚀 Cómo ejecutar

1️⃣ Crear entorno virtual y dependencias:
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2️⃣ Ejecutar los tres nodos:
```bash
bash scripts/run_all.sh
```

3️⃣ Abrir en el navegador:
- http://127.0.0.1:5001  
- http://127.0.0.1:5002  
- http://127.0.0.1:5003  

---

## 🧪 Pruebas
- **Read-Your-Writes (RYW):** el usuario ve sus propias escrituras al leer en otro nodo.  
- **Monotonic Reads (MR):** nunca lee una versión más vieja.  
- **Writes-Follow-Reads (WFR):** una escritura espera a que lleguen las lecturas previas de la sesión.

---

## 👨‍💻 Autores
- Joana Fernandez  
- Abril Calatayud  
- Agustín Gimenez  
- Martin Crespo
