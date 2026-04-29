from flask import Flask, jsonify, request
from flask_cors import CORS
import requests
import xml.etree.ElementTree as ET

app = Flask(__name__)
CORS(app)  # Permite que el navegador consulte este servidor

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; CUITConsulta/1.0)",
    "Accept": "application/json, text/xml, */*"
}

TIMEOUT = 10

# ── REPET ─────────────────────────────────────────────────────────────────────
@app.route("/repet/<cuit>")
def repet(cuit):
    try:
        url = f"https://repet.jus.gob.ar/xml.php?cuit={cuit}"
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        root = ET.fromstring(res.text)
        personas = root.findall("persona")

        if not personas:
            return jsonify({"estado": "libre", "mensaje": "No figura en el listado de terroristas", "registros": []})

        registros = []
        for p in personas:
            registros.append({
                "nombre":  p.findtext("nombre", "—"),
                "tipo":    p.findtext("tipo",   "—"),
                "motivo":  p.findtext("motivo", "—"),
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

        # La respuesta es HTML — buscamos indicadores clave
        html = res.text.lower()

        if "no se encontraron resultados" in html or "sin resultado" in html:
            return jsonify({"estado": "no_encontrado", "mensaje": "No figura como sujeto obligado ante la UIF"})

        if "sujeto obligado" in html or "actividad" in html:
            return jsonify({"estado": "encontrado", "mensaje": "Figura como Sujeto Obligado ante la UIF", "link": url})

        return jsonify({"estado": "manual", "mensaje": "No se pudo determinar automáticamente", "link": f"https://www.uif.gob.ar/uif/index.php/es/sujetos-obligados"})

    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)}), 500


# ── SIPRO / Proveedor del Estado ──────────────────────────────────────────────
@app.route("/sipro/<cuit>")
def sipro(cuit):
    try:
        url = f"https://www.argentinacompra.gov.ar/prod/onc/sitio/Paginas/Sipro/buscarProveedores.aspx?cuit={cuit}"
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        html = res.text.lower()

        if "no se encontraron" in html or "sin resultados" in html:
            return jsonify({"estado": "no_encontrado", "mensaje": "No figura en el padrón de proveedores del Estado"})

        # Intentar extraer datos básicos del HTML
        nombre = ""
        estado_hab = ""

        if "razon social" in html or "razón social" in html or "denominacion" in html:
            return jsonify({
                "estado": "encontrado",
                "mensaje": "Figura en el padrón de proveedores del Estado",
                "link": url
            })

        return jsonify({"estado": "manual", "mensaje": "Verificar manualmente en SIPRO", "link": url})

    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)}), 500


# ── CONSEJO DE SEGURIDAD ONU ──────────────────────────────────────────────────
@app.route("/onu/<cuit>")
def onu(cuit):
    try:
        # La ONU tiene una API pública de consulta de sanciones
        # Usamos el nombre si lo tenemos, pero con CUIT buscamos por documento
        url = f"https://scsanctions.un.org/resources/xml/en/consolidated.xml"

        # Para no descargar todo el XML cada vez, consultamos la API REST de la ONU
        api_url = f"https://scsanctions.un.org/api/search?term={cuit}&limit=5"
        res = requests.get(api_url, headers=HEADERS, timeout=TIMEOUT)

        if res.status_code == 200:
            data = res.json()
            if data.get("results") and len(data["results"]) > 0:
                registros = []
                for r in data["results"]:
                    registros.append({
                        "nombre": r.get("name", "—"),
                        "tipo": r.get("type", "—"),
                        "referencia": r.get("reference", "—"),
                    })
                return jsonify({"estado": "alerta", "mensaje": "FIGURA EN LISTA DE SANCIONES ONU", "registros": registros})
            else:
                return jsonify({"estado": "libre", "mensaje": "No figura en la lista de sanciones del Consejo de Seguridad ONU"})
        else:
            return jsonify({"estado": "manual", "mensaje": "Consultar manualmente en el sitio de la ONU", "link": "https://scsanctions.un.org/search/"})

    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)}), 500


# ── PEP ───────────────────────────────────────────────────────────────────────
@app.route("/pep/<cuit>")
def pep(cuit):
    try:
        # Intentar API de la UIF para PEP
        url = f"https://www.uif.gob.ar/uif/index.php/es/component/pep/?cuit={cuit}"
        res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        html = res.text.lower()

        if "no se encontraron" in html or "sin resultado" in html:
            return jsonify({"estado": "libre", "mensaje": "No figura como Persona Expuesta Políticamente"})

        if "persona expuesta" in html or "pep" in html or "cargo" in html or "funcion" in html:
            return jsonify({
                "estado": "alerta",
                "mensaje": "FIGURA COMO PERSONA EXPUESTA POLÍTICAMENTE",
                "link": url
            })

        return jsonify({
            "estado": "manual",
            "mensaje": "Verificar manualmente en la base PEP de la UIF",
            "link": "https://www.uif.gob.ar/uif/index.php/es/bases-de-datos"
        })

    except Exception as e:
        return jsonify({"estado": "error", "mensaje": str(e)}), 500


# ── Health check ──────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return jsonify({"status": "ok", "servicio": "Consulta CUIT/CUIL Argentina"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
