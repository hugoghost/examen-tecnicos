import json
import os
import sqlite3
import random
from flask import Flask, render_template, request, redirect, url_for

app = Flask(__name__)

DB_FILE = "respuestas_tecnicos.db"
PREGUNTAS_FILE = "preguntas.json"

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
        nombre = request.form["nombre"]
        correo = request.form["correo"]
        telefono = request.form["telefono"]
        return redirect(url_for("examen", nombre=nombre, correo=correo, telefono=telefono))
    return render_template("index.html")

@app.route("/examen")
def examen():
    nombre = request.args.get("nombre")
    correo = request.args.get("correo")
    telefono = request.args.get("telefono")
    preguntas = cargar_preguntas()
    preguntas_aleatorias = random.sample(preguntas, 15)
    for p in preguntas_aleatorias:
        random.shuffle(p["opciones"])
    return render_template("examen.html", preguntas=preguntas_aleatorias, nombre=nombre, correo=correo, telefono=telefono)

@app.route("/guardar_respuestas", methods=["POST"])
def guardar_respuestas():
    datos = request.form
    nombre = datos.get("nombre")
    correo = datos.get("correo")
    telefono = datos.get("telefono")
    respuestas = json.dumps([datos.get(f"respuesta_{i}") for i in range(15)], ensure_ascii=False)
    tiempos = json.dumps([datos.get(f"tiempo_{i}") for i in range(15)], ensure_ascii=False)
    tiempo_total = datos.get("tiempo_total")
    ip = request.remote_addr

    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO respuestas (nombre, correo, telefono, respuestas, tiempos, tiempo_total, ip)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (nombre, correo, telefono, respuestas, tiempos, tiempo_total, ip))
    conn.commit()
    conn.close()
    return redirect(url_for("gracias"))

@app.route("/gracias")
def gracias():
    return render_template("gracias.html")

# Nueva página de resultados general
@app.route("/resultados", methods=["GET"])
def resultados():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT DISTINCT nombre FROM respuestas")
    tecnicos = [row[0] for row in c.fetchall()]
    conn.close()
    return render_template("resultados.html", tecnicos=tecnicos)

# Resultados individuales por técnico
@app.route("/resultados/tecnico", methods=["GET"])
def resultados_tecnico():
    nombre = request.args.get("nombre")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT id, nombre, correo, telefono, respuestas, tiempos, tiempo_total, ip 
        FROM respuestas WHERE nombre = ?
    """, (nombre,))
    resultados = c.fetchall()
    conn.close()
    return render_template("resultados_tecnico.html", resultados=resultados, nombre=nombre)

# Borrar todos los resultados (opcional/admin)
@app.route("/borrar_resultados", methods=["POST"])
def borrar_resultados():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("DELETE FROM respuestas")
    conn.commit()
    conn.close()
    return redirect(url_for("resultados"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
