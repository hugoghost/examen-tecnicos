import os, sqlite3, json, random
from flask import Flask, render_template, request, session, redirect, url_for

app = Flask(__name__)
app.secret_key = 'clave_super_secreta_y_larga'

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

def cargar_preguntas():
    with open(PREGUNTAS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

crear_db()

@app.route("/", methods=["GET","POST"])
def index():
    if request.method == "POST":
        # Guardamos datos del técnico
        session.clear()
        session["nombre"] = request.form["nombre"]
        session["correo"] = request.form["correo"]
        session["telefono"] = request.form["telefono"]

        # Barajamos y seleccionamos 15 preguntas al azar
        preguntas = random.sample(cargar_preguntas(), k=15)
        for p in preguntas:
            random.shuffle(p["opciones"])
        session["preguntas"] = preguntas

        # Inicializamos respuestas y tiempos
        session["respuestas"] = []
        session["tiempos"] = []
        session["tiempo_total"] = 0
        session["actual"] = 0

        return redirect(url_for("examen"))

    return render_template("index.html")


@app.route("/examen", methods=["GET","POST"])
def examen():
    if "preguntas" not in session:
        return redirect(url_for("index"))

    actual = session["actual"]
    preguntas = session["preguntas"]

    if request.method == "POST":
        # Recogemos la respuesta y el tiempo usado
        resp = request.form.get("respuesta","")
        tiempo = float(request.form.get("tiempo","60"))

        session["respuestas"].append(resp)
        session["tiempos"].append(tiempo)
        session["tiempo_total"] += tiempo
        session["actual"] += 1
        actual = session["actual"]

    # Si aún quedan preguntas, la mostramos
    if actual < len(preguntas):
        return render_template(
            "examen.html",
            pregunta=preguntas[actual],
            num=actual+1,
            total=len(preguntas)
        )

    # Si ya terminó, guardamos en la BD y vamos a “gracias”
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        INSERT INTO respuestas
        (nombre, correo, telefono, respuestas, tiempos, tiempo_total, ip)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        session["nombre"],
        session["correo"],
        session["telefono"],
        json.dumps(session["respuestas"], ensure_ascii=False),
        json.dumps(session["tiempos"], ensure_ascii=False),
        session["tiempo_total"],
        request.remote_addr
    ))
    conn.commit()
    conn.close()
    session.clear()
    return redirect(url_for("gracias"))


@app.route("/gracias")
def gracias():
    return render_template("gracias.html")


@app.route("/resultados")
def resultados():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT id, nombre, correo, telefono, tiempo_total, ip FROM respuestas")
    rows = c.fetchall()
    conn.close()
    return render_template("resultados.html", resultados=rows)


@app.route("/resultado/<int:res_id>")
def resultados_tecnico(res_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        SELECT nombre, correo, telefono, respuestas, tiempos, tiempo_total, ip
        FROM respuestas WHERE id=?
    """, (res_id,))
    row = c.fetchone()
    conn.close()

    # Para el detalle, volvemos a cargar la lista completa de preguntas
    preguntas = cargar_preguntas()
    user_resps = json.loads(row[3])
    user_times = json.loads(row[4])

    detalles = []
    for i, ur in enumerate(user_resps):
        p = preguntas[i]
        correcta_idx = p.get("respuestaCorrecta", 0)
        correcta_text = p["opciones"][correcta_idx]
        detalles.append({
            "pregunta": p["pregunta"],
            "respuesta_usuario": ur,
            "respuesta_correcta": correcta_text,
            "acierto": ur == correcta_text,
            "tiempo": user_times[i] if i < len(user_times) else 0
        })

    return render_template(
        "resultados_tecnico.html",
        nombre=row[0],
        correo=row[1],
        telefono=row[2],
        tiempo_total=row[5],
        ip=row[6],
        detalles=detalles
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
