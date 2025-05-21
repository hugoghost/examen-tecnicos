import json
import os
import sqlite3
import random
from flask import Flask, render_template, request, jsonify

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
                tiempo_total REAL
            )
        """)
        conn.commit()
        conn.close()

def cargar_preguntas():
    with open(PREGUNTAS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/get_preguntas", methods=["GET"])
def get_preguntas():
    preguntas = cargar_preguntas()
    preguntas_aleatorias = random.sample(preguntas, len(preguntas))
    return jsonify(preguntas_aleatorias)

@app.route("/guardar", methods=["POST"])
def guardar():
    data = request.get_json()
    nombre = data.get("nombre")
    correo = data.get("correo")
    telefono = data.get("telefono")
    respuestas = data.get("respuestas")
    tiempos = data.get("tiempos")
    tiempo_total = data.get("tiempo_total")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("INSERT INTO respuestas (nombre, correo, telefono, respuestas, tiempos, tiempo_total) VALUES (?, ?, ?, ?, ?, ?)",
              (nombre, correo, telefono, json.dumps(respuestas, ensure_ascii=False), json.dumps(tiempos), tiempo_total))
    conn.commit()
    conn.close()
    return jsonify({"status": "ok"})

@app.route("/resultados")
def resultados():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT nombre, correo FROM respuestas")
    filas = c.fetchall()
    conn.close()
    html = "<h2>Lista de técnicos</h2><ul>"
    for nombre, correo in filas:
        html += f"<li><a href='/resultados/tecnico?nombre={nombre}&correo={correo}'>{nombre} ({correo})</a></li>"
    html += "</ul>"
    html += "<br><hr><p>Selecciona un técnico para ver el detalle de sus respuestas.</p>"
    return html

@app.route("/resultados/tecnico")
def resultado_tecnico():
    nombre = request.args.get("nombre")
    correo = request.args.get("correo")
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT nombre, correo, telefono, respuestas, tiempos, tiempo_total FROM respuestas WHERE nombre=? AND correo=?", (nombre, correo))
    fila = c.fetchone()
    conn.close()
    preguntas_banco = cargar_preguntas()

    if not fila:
        return f"No se encontró el técnico {nombre} ({correo})"

    nombre, correo, telefono, respuestas_str, tiempos_str, tiempo_total = fila
    respuestas = json.loads(respuestas_str)
    tiempos = json.loads(tiempos_str)

    html = f"<h2>Detalle de {nombre} ({correo})</h2>"
    html += f"<p><b>Teléfono:</b> {telefono}</p>"
    html += "<table border=1><tr><th>#</th><th>Pregunta</th><th>Respuesta</th><th>Correcta</th><th>Tiempo (s)</th></tr>"
    for i, r in enumerate(respuestas):
        if i < len(preguntas_banco):
            pregunta = preguntas_banco[i]
            correcta = pregunta["opciones"][pregunta["respuestaCorrecta"]]
            try:
                resp_idx = int(r)
                respuesta = pregunta["opciones"][resp_idx] if resp_idx != -1 else "Sin respuesta"
                es_correcta = "✅" if resp_idx == pregunta["respuestaCorrecta"] else "❌"
            except:
                respuesta = "Sin respuesta"
                es_correcta = ""
            tpo = tiempos[i] if i < len(tiempos) else ""
            html += f"<tr><td>{i+1}</td><td>{pregunta['pregunta']}</td><td>{respuesta}</td><td>{correcta} {es_correcta}</td><td>{tpo:.2f}</td></tr>"
    html += f"<tr><td colspan='4'><b>Tiempo total</b></td><td><b>{tiempo_total:.2f} s</b></td></tr>"
    html += "</table>"
    html += "<br><a href='/resultados'>⬅ Volver a la lista</a>"
    return html

if __name__ == "__main__":
    crear_db()
    app.run(host="0.0.0.0", port=5000)
