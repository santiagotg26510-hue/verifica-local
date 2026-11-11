import os
import requests
from flask import Flask, render_template, request, jsonify

app = Flask(__name__)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

SYSTEM_PROMPT = """
Eres Veri铿乧a Local, un asistente de verificaci贸n period铆stica en espa帽ol.
Investiga la afirmaci贸n usando la b煤squeda web disponible. No inventes fuentes,
fechas, citas ni datos. Distingue entre la afirmaci贸n exacta y el contexto.
Prioriza fuentes primarias y organismos oficiales, despu茅s medios reconocidos
y verificadores independientes. Busca corroboraci贸n y contradicciones.

Responde SIEMPRE en espa帽ol con esta estructura:
VEREDICTO: una sola categor铆a: VERDADERA, FALSA, ENGA脩OSA o NO COMPROBADA
RESUMEN: explicaci贸n breve y clara.
EVIDENCIA A FAVOR: puntos concretos o "No se encontr贸 evidencia suficiente".
EVIDENCIA EN CONTRA: puntos concretos o "No se encontr贸 evidencia suficiente".
CONTEXTO: fecha, lugar o matices importantes, si aplican.
CONFIANZA: ALTA, MEDIA o BAJA, explicando brevemente por qu茅.
IMPORTANTE: "NO COMPROBADA" significa que no hay evidencia suficiente; no
significa que sea falsa. Si la noticia mezcla datos ciertos con una conclusi贸n
incorrecta, usa ENGA脩OSA. No afirmes certeza absoluta.
"""

@app.get("/")
def home():
    return render_template("index.html", configured=bool(GEMINI_API_KEY))

@app.post("/api/verificar")
def verificar():
    data = request.get_json(silent=True) or {}
    claim = (data.get("claim") or "").strip()
    if len(claim) < 8:
        return jsonify(error="Escribe una afirmaci贸n o noticia un poco m谩s completa."), 400
    if len(claim) > 5000:
        return jsonify(error="El texto es demasiado largo. M谩ximo 5,000 caracteres."), 400
    if not GEMINI_API_KEY:
        return jsonify(error="Falta configurar GEMINI_API_KEY en el servidor. Consulta INSTRUCCIONES.txt."), 503

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
    payload = {
        "system_instruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text":
            "Verifica esta afirmaci贸n/noticia. Si incluyo un enlace, 煤salo como pista, "
            "pero contrasta la afirmaci贸n con otras fuentes independientes:\n\n" + claim
        }]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 1400}
    }
    try:
        response = requests.post(
            url,
            params={"key": GEMINI_API_KEY},
            json=payload,
            timeout=90
        )
        if response.status_code >= 400:
            try:
                detail = response.json().get("error", {}).get("message", "Error del servicio de IA.")
            except Exception:
                detail = "Error del servicio de IA."
            return jsonify(error=f"No se pudo completar la verificaci贸n: {detail}"), 502

        result = response.json()
        candidate = (result.get("candidates") or [{}])[0]
        parts = candidate.get("content", {}).get("parts", [])
        answer = "\n".join(p.get("text", "") for p in parts if p.get("text"))
        metadata = candidate.get("groundingMetadata", {})
        sources = []
        seen = set()
        for chunk in metadata.get("groundingChunks", []):
            web = chunk.get("web", {})
            uri = web.get("uri")
            title = web.get("title") or uri
            if uri and uri not in seen:
                seen.add(uri)
                sources.append({"title": title, "url": uri})
        queries = metadata.get("webSearchQueries", [])
        if not answer:
            return jsonify(error="La IA no devolvi贸 un an谩lisis. Int茅ntalo de nuevo."), 502
        return jsonify(answer=answer, sources=sources, queries=queries)
    except requests.Timeout:
        return jsonify(error="La b煤squeda tard贸 demasiado. Int茅ntalo de nuevo."), 504
    except requests.RequestException:
        return jsonify(error="No se pudo conectar con el servicio de verificaci贸n."), 502

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
