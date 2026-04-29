from flask import Flask, jsonify, send_file
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET
import os

app = Flask(__name__)
CORS(app)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CUITConsulta/1.0)",
    "Accept": "application/json, text/xml, */*"
}
TIMEOUT = 10

# ── Página principal ──────────────────────────────────────────────────────────
@app.route("/")
def index():
    return send_file("index.html")

# ── REPET ─────────────────────────────────────────────────────────────────────
@app.route("/repet/<cuit>")
def repet(cuit):
    try:
        url = f"https://repet.jus.gob.ar/xml.php?cuit={cuit}"
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        root = ET.fromstring(res.text)
        personas = root.findall("persona")
        if not personas:
            return jsonify({"estado": "libre", "mensaje": "No figura en el listado de terroristas"})
        registros = []
        for p in personas:
            registros.append({
                "nombre": p.findtext("nombre", "—"),
                "tipo":   p.findtext("tipo",   "—"),
                "motivo": p.findtext("motivo", "—"),
            })
        return jsonify({"estado": "alerta", "mensaje": "FIGURA EN LISTADO DE TERRORISTAS", "registros": registros})
    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)}), 500

# ── SUJETO OBLIGADO UIF ───────────────────────────────────────────────────────
@app.route("/uif/<cuit>")
def uif(cuit):
    try:
        url = f"https://www.uif.gob.ar/uif/index.php/es/component/sujoblig/?cuit={cuit}"
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        html = res.text.lower()
        if "no se encontraron resultados" in html or "sin resultado" in html:
            return jsonify({"estado": "no_encontrado", "mensaje": "No figura como sujeto obligado ante la UIF"})
        if "sujeto obligado" in html or "actividad" in html:
            return jsonify({"estado": "encontrado", "mensaje": "Figura como Sujeto Obligado ante la UIF",
                            "link": "https://www.uif.gob.ar/uif/index.php/es/sujetos-obligados"})
        return jsonify({"estado": "manual", "mensaje": "No se pudo determinar automáticamente",
                        "link": "https://www.uif.gob.ar/uif/index.php/es/sujetos-obligados"})
    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)}), 500

# ── SIPRO ─────────────────────────────────────────────────────────────────────
@app.route("/sipro/<cuit>")
def sipro(cuit):
    try:
        url = f"https://www.argentinacompra.gov.ar/prod/onc/sitio/Paginas/Sipro/buscarProveedores.aspx?cuit={cuit}"
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        html = res.text.lower()
        if "no se encontraron" in html or "sin resultados" in html:
            return jsonify({"estado": "no_encontrado", "mensaje": "No figura en el padrón de proveedores del Estado"})
        if "razon social" in html or "razón social" in html or "denominacion" in html:
            return jsonify({"estado": "encontrado", "mensaje": "Figura en el padrón de proveedores del Estado", "link": url})
        return jsonify({"estado": "manual", "mensaje": "Verificar manualmente en SIPRO",
                        "link": "https://www.argentinacompra.gov.ar/prod/onc/sitio/Paginas/Sipro/buscarProveedores.aspx"})
    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)}), 500

# ── CONSEJO DE SEGURIDAD ONU ──────────────────────────────────────────────────
@app.route("/onu/<cuit>")
def onu(cuit):
    try:
        api_url = f"https://scsanctions.un.org/api/search?term={cuit}&limit=5"
        res = requests.get(api_url, headers=HEADERS, timeout=TIMEOUT)
        if res.status_code == 200:
            data = res.json()
            if data.get("results") and len(data["results"]) > 0:
                registros = [{"nombre": r.get("name","—"), "tipo": r.get("type","—"), "referencia": r.get("reference","—")} for r in data["results"]]
                return jsonify({"estado": "alerta", "mensaje": "FIGURA EN LISTA DE SANCIONES ONU", "registros": registros})
            return jsonify({"estado": "libre", "mensaje": "No figura en la lista de sanciones ONU"})
        return jsonify({"estado": "manual", "mensaje": "Consultar manualmente", "link": "https://scsanctions.un.org/search/"})
    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)}), 500

# ── PEP ───────────────────────────────────────────────────────────────────────
@app.route("/pep/<cuit>")
def pep(cuit):
    try:
        url = f"https://www.uif.gob.ar/uif/index.php/es/component/pep/?cuit={cuit}"
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        html = res.text.lower()
        if "no se encontraron" in html or "sin resultado" in html:
            return jsonify({"estado": "libre", "mensaje": "No figura como Persona Expuesta Políticamente"})
        if "persona expuesta" in html or "cargo" in html or "funcion" in html:
            return jsonify({"estado": "alerta", "mensaje": "FIGURA COMO PERSONA EXPUESTA POLÍTICAMENTE", "link": url})
        return jsonify({"estado": "manual", "mensaje": "Verificar manualmente en la base PEP de la UIF",
                        "link": "https://www.uif.gob.ar/uif/index.php/es/bases-de-datos"})
    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
