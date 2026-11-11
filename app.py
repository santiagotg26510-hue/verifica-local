
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
        return jsonify({"error": "Escribe una noticia."}), 400

    if not API_KEY:
        return jsonify({"error": "No está configurada la API Key."}), 500

    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        + MODEL + ":generateContent"
    )

    prompt = f"""
    Actúa como verificador de información.
    Analiza esta afirmación:
    {noticia}

    Contrasta los datos usando Google Search.
    Responde en español e incluye:
    VEREDICTO: VERDADERA, FALSA, ENGAÑOSA o NO COMPROBADA.
    RESUMEN:
    EVIDENCIAS:
    FUENTES Y ENLACES:
    CONFIANZA: alta, media o baja.

    No inventes información ni fuentes.
    Si no hay pruebas suficientes, indícalo.
    """

    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "tools": [
            {"google_search": {}}
        ]
    }

    try:
        respuesta = requests.post(
            url,
            params={"key": API_KEY},
            json=payload,
            timeout=90
        )

        if not respuesta.ok:
            try:
                error = respuesta.json().get("error", {})
                mensaje = error.get("message", "Error desconocido")
            except Exception:
                mensaje = "Google rechazó la solicitud."

            return jsonify({
                "error": f"Google API ({respuesta.status_code}): {mensaje}"
            }), 502

        resultado = respuesta.json()

        candidatos = resultado.get("candidates", [])
        if not candidatos:
            return jsonify({
                "error": "Google no devolvió una respuesta. Intenta otra vez."
            }), 502

        partes = candidatos[0].get("content", {}).get("parts", [])
        texto = "\n".join(
            parte.get("text", "")
            for parte in partes
            if parte.get("text")
        )

        if not texto:
            return jsonify({
                "error": "La respuesta de Google llegó vacía."
            }), 502

        return jsonify({"resultado": texto})

    except requests.exceptions.Timeout:
        return jsonify({
            "error": "Google tardó demasiado en responder."
        }), 504

    except requests.exceptions.RequestException:
        return jsonify({
            "error": "No se pudo conectar con Google."
        }), 502

    except Exception:
        app.logger.exception("Error inesperado")
        return jsonify({
            "error": "Ocurrió un error interno del servidor."
        }), 500


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 5000))
    )
    
