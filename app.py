
import os
import requests
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

API_KEY = os.environ.get("GEMINI_API_KEY")
MODEL = "gemini-3.8-flash"

@app.route("/")
def inicio():
    return render_template("index.html")

@app.route("/api/verificar", methods=["POST"])
def verificar():
    data = request.get_json(silent=True) or {}
    noticia = data.get("noticia", "").strip()

    if not noticia:
        return jsonify({
            "error": "Escribe una noticia para verificar."
        }), 400

    if not API_KEY:
        return jsonify({
            "error": "Falta configurar la API Key de Gemini."
        }), 500

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + MODEL
        + ":generateContent?key="
        + API_KEY
    )

    prompt = f"""
    Eres un asistente especializado en verificación de noticias.

    Analiza cuidadosamente la siguiente noticia:

    {noticia}

    Contrasta la información utilizando Google Search.

    Responde en español con:
    1. VEREDICTO: VERDADERA, FALSA, ENGAÑOSA o NO COMPROBADA.
    2. RESUMEN de lo que afirma.
    3. EVIDENCIAS que apoyen o contradigan la afirmación.
    4. FUENTES consultadas con sus enlaces.
    5. NIVEL DE CONFIANZA: alto, medio o bajo.

    No inventes fuentes ni afirmes que algo es verdadero
    cuando no existan pruebas suficientes.
    """

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "tools": [
            {
                "google_search": {}
            }
        ]
    }

    try:
        respuesta = requests.post(
            url,
            json=payload,
            timeout=60
        )

        respuesta.raise_for_status()
        resultado = respuesta.json()

        texto = resultado["candidates"][0]["content"]["parts"][0]["text"]

        return jsonify({
            "resultado": texto
        })

    except requests.exceptions.HTTPError:
        return jsonify({
            "error": "Google no pudo procesar la noticia. Revisa el modelo y la API Key."
        }), 502

    except Exception:
        return jsonify({
            "error": "No se pudo completar la verificación. Intenta nuevamente."
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
