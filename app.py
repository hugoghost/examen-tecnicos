import os
import sqlite3
import json
import random
from flask import Flask, render_template, request, redirect, url_for, session, flash

app = Flask(__name__)
app.secret_key = 'clave_super_secreta_y_larga'

DB_FILE = "respuestas_tecnicos.db"
PREGUNTAS_FILE = "preguntas.json"

# Configura aquí tus credenciales de administrador
ADMIN_USER = 'admin'
ADMIN_PASS = 'admin123'

def crear_db():
    if not os.path.exists(DB_FILE):
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
        CREATE TABLE respuestas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            correo TEXT,
            telefono TEXT,
            respuestas TEXT,
            tiempos TEXT,
            tiempo_total REAL,
            ip TEXT
        )
        """)
        conn.commit()
        conn.close()

crear_db()

def cargar_preguntas():
    with open(PREGUNTAS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        session.clear()
        session["nombre"] = request.form["nombre"]
        session["correo"] = request.form["correo"]
        session["telefono"] = request.form["telefono"]
        preguntas = random.sample(cargar_preguntas(), 15)
        for pregunta in preguntas:
            opciones = pregunta["opciones"][:]
            random.shuffle(opciones)
            pregunta["opciones_random"] = opciones
        session["preguntas"] = preguntas
        session["respuestas"] = []
        session["tiempos"] = []
        session["tiempo_total"] = 0
        session["actual"] = 0
        return redirect(url_for("examen"))
    return render_template("index.html")

@app.route("/examen", methods=["GET", "POST"])
def examen():
    if "nombre" not in session or "preguntas" not in session:
        return redirect(url_for("index"))
    preguntas = session["preguntas"]
    actual = session["actual"]
    if request.method == "POST":
        respuesta = request.form.get("respuesta")
        tiempo = request.form.get("tiempo")
        session["respuestas"].append(respuesta)
        session["tiempos"].append(tiempo)
        session["tiempo_total"] += float(tiempo)
        session["actual"] += 1
        actual = session["actual"]
    if actual < len(preguntas):
        pregunta = preguntas[actual]
        num = actual + 1
        total = len(preguntas)
        return render_template("examen.html", pregunta=pregunta, num=num, total=total, tiempo_restante=60)
    else:
        # Guardar en BD
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute("""
            INSERT INTO respuestas (nombre, correo, telefono, respuestas, tiempos, tiempo_total, ip)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            session["nombre"],
            session["correo"],
            session["telefono"],
            json.dumps(session["respuestas"]),
            json.dumps(session["tiempos"]),
            session["tiempo_total"],
            request.remote_addr
        ))
        conn.commit()
        conn.close()
        tiempo_total = session["tiempo_total"]
        session.clear()
        return render_template("gracias.html", tiempo_total=tiempo_total)

@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username == ADMIN_USER and password == ADMIN_PASS:
            session["admin_logged_in"] = True
            return redirect(url_for("admin_panel"))
        else:
            flash("Usuario o contraseña incorrectos")
    return render_template("admin_login.html")

@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_logged_in", None)
    return redirect(url_for("admin_login"))

def admin_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get("admin_logged_in"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated

@app.route("/admin")
@admin_required
def admin_panel():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, nombre, correo, telefono, tiempo_total, ip FROM respuestas ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return render_template("resultados.html", resultados=rows)

@app.route("/admin/detalle/<int:res_id>")
@admin_required
def admin_detalle(res_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT nombre, correo, telefono, respuestas, tiempos, tiempo_total, ip FROM respuestas WHERE id=?", (res_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return "No encontrado", 404
    preguntas = cargar_preguntas()
    respuestas = json.loads(row[3])
    tiempos = json.loads(row[4])
    detalles = []
    for i, resp in enumerate(respuestas):
        if i < len(preguntas):
            pregunta = preguntas[i]
            correcta_idx = pregunta["respuestaCorrecta"]
            correcta = pregunta["opciones"][correcta_idx]
        else:
            pregunta = {"pregunta": "(no disponible)", "opciones": []}
            correcta = "(no disponible)"
        acierto = resp == str(correcta)
        detalles.append({
            "pregunta": pregunta["pregunta"],
            "respuesta_usuario": resp,
            "respuesta_correcta": correcta,
            "acierto": acierto,
            "tiempo": tiempos[i] if i < len(tiempos) else ""
        })
    return render_template("resultados_tecnico.html",
        nombre=row[0], correo=row[1], telefono=row[2],
        tiempo_total=row[5], ip=row[6], detalles=detalles
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
