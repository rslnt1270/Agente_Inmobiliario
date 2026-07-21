"""Scraper de renta (departamento/casa) en Ciudad Nezahualcóyotl vía Doomos.

Método: httpx (HTTP/2) — sin Selenium. Doomos es una app Next.js con
renderizado en servidor (RSC): el HTML estático NO contiene los listados en
markup normal, sino que cada "página" de datos viaja como un blob de texto
dentro de llamadas `self.__next_f.push([1, "<string JSON-escapado>"])`
incrustadas en `<script>` tags. Se extrae así:

  1. Regex "escape-aware" sobre el HTML para capturar el argumento string de
     cada `self.__next_f.push([1, "..."])`, respetando comillas escapadas
     (`\\"`) dentro del string — un regex ingenuo que solo busca `"..."` corta
     el string en la primera comilla escapada.
  2. Cada string capturado se decodifica con `json.loads('"' + s + '"')`, que
     revierte el escapado JSON estándar (\\", \\r\\n, etc.) y produce el texto
     JS/JSON real embebido (confirmado en vivo 2026-07-21: el payload es
     válido tras un solo nivel de unescape).
  3. Sobre ese texto ya "desescapado" se localizan objetos balanceados que
     empiezan en `{"id":` (equilibrando llaves y respetando comillas/escapes)
     y se valida cada uno con `json.loads`, quedándose solo con los que
     contienen las claves `listing_type` y `price` (i.e. son anuncios, no
     metadata de breadcrumbs/SEO/etc. del mismo payload).

Confirmado en vivo contra `https://www.doomos.com.mx/renta/departamentos/
ciudad-nezahualcoyotl` (3 anuncios) y `.../renta/casas/ciudad-nezahualcoyotl`
(1 anuncio — el glitch conocido de una "casa" en venta por $2.7M mal
etiquetada como listing_type Renta, mencionado en el brief).

URL de detalle: no hay `href` explícito en el payload de listado; se
construye `https://www.doomos.com.mx/propiedad/<slug>`, patrón verificado
en vivo (200, contenido de la propiedad coincide con el precio/título del
listado).
"""
from __future__ import annotations

import argparse
import json
import re
import sys

import httpx

from config import get_headers, polite_sleep
from utils import clean_text, parse_precio

FUENTE = "doomos"
_BASE_URL = "https://www.doomos.com.mx"

FEEDS_ZONA = [
    "https://www.doomos.com.mx/renta/departamentos/ciudad-nezahualcoyotl",
    "https://www.doomos.com.mx/renta/casas/ciudad-nezahualcoyotl",
]

# Captura el string argumento de self.__next_f.push([1,"..."]) respetando
# comillas escapadas (\") dentro del contenido.
_PUSH_RE = re.compile(r'self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)')


def _extraer_blobs_desescapados(html: str) -> list[str]:
    """Devuelve el texto desescapado de cada self.__next_f.push([1, "..."]) del HTML."""
    blobs = []
    for raw in _PUSH_RE.findall(html):
        try:
            texto = json.loads('"' + raw + '"')
        except (json.JSONDecodeError, ValueError):
            continue
        blobs.append(texto)
    return blobs


def _objetos_balanceados(texto: str, marca: str = '{"id":') -> list[str]:
    """Extrae substrings de objetos JSON balanceados que empiezan en `marca`.

    Recorre carácter a carácter contando llaves, ignorando las que están
    dentro de strings (y respetando el escape `\\` dentro de esas strings),
    para no cortar objetos anidados (arrays de imágenes, sub-objetos city/
    state/property_type, etc.) a la mitad.
    """
    objetos = []
    idx = 0
    n = len(texto)
    while True:
        i = texto.find(marca, idx)
        if i == -1:
            break
        depth = 0
        j = i
        en_str = False
        escape = False
        fin = None
        while j < n:
            ch = texto[j]
            if en_str:
                if escape:
                    escape = False
                elif ch == "\\":
                    escape = True
                elif ch == '"':
                    en_str = False
            else:
                if ch == '"':
                    en_str = True
                elif ch == "{":
                    depth += 1
                elif ch == "}":
                    depth -= 1
                    if depth == 0:
                        fin = j
                        break
            j += 1
        if fin is None:
            break
        objetos.append(texto[i:fin + 1])
        idx = fin + 1
    return objetos


def _extraer_listados(html: str) -> list[dict]:
    """Extrae los objetos JSON de anuncio (con listing_type + price) del HTML."""
    listados: list[dict] = []
    for blob in _extraer_blobs_desescapados(html):
        if '"listing_type"' not in blob or '"price"' not in blob:
            continue
        for obj_str in _objetos_balanceados(blob):
            try:
                obj = json.loads(obj_str)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict) and "listing_type" in obj and "price" in obj:
                listados.append(obj)
    return listados


def _obj_a_crudo(obj: dict) -> dict | None:
    """Convierte un objeto de anuncio Doomos al registro crudo del contrato de zona."""
    slug = obj.get("slug")
    if not slug:
        return None
    url = f"{_BASE_URL}/propiedad/{slug}"

    titulo = clean_text(obj.get("title")) or ""
    ciudad = clean_text((obj.get("city") or {}).get("name")) or ""

    tipo = "departamento"
    prop_type = clean_text((obj.get("property_type") or {}).get("name"))
    if prop_type:
        prop_type_lower = prop_type.lower()
        if "casa" in prop_type_lower:
            tipo = "casa"
        elif "departamento" in prop_type_lower:
            tipo = "departamento"
        else:
            tipo = prop_type_lower

    return {
        "precio": parse_precio(str(obj.get("price"))) if obj.get("price") is not None else None,
        "tipo_inmueble": tipo,
        "m2": obj.get("area_m2"),
        "recamaras": obj.get("bedrooms"),
        "banos": obj.get("bathrooms"),
        "estacionamientos": obj.get("parking_spots") or obj.get("parking") or None,
        "url": url,
        "publicado_por": None,  # no hay campo de agencia en el listado
        "telefono": obj.get("contact_phone"),
        "texto": f"{titulo} {ciudad} {url}",
        "fuente": FUENTE,
    }


def parse_zona_html(html: str) -> list[dict]:
    """Parsea el HTML (con blobs RSC) de un listado de zona y devuelve registros crudos."""
    out = []
    for obj in _extraer_listados(html):
        reg = _obj_a_crudo(obj)
        if reg is not None:
            out.append(reg)
    return out


def scrape_zona() -> list[dict]:
    """Descarga los feeds de la franja Alameda Oriente y devuelve registros crudos.

    Un feed que falle (error de red, status != 200, o payload sin listados
    extraíbles) se omite sin abortar los demás.
    """
    regs: list[dict] = []
    with httpx.Client(http2=True, follow_redirects=True, timeout=25) as client:
        for i, url in enumerate(FEEDS_ZONA):
            try:
                r = client.get(url, headers=get_headers())
            except Exception as exc:
                print(f"[doomos] ERROR al pedir {url}: {exc}", file=sys.stderr)
                r = None

            if r is not None and r.status_code == 200:
                regs.extend(parse_zona_html(r.text))
            elif r is not None:
                print(f"[doomos] AVISO: status {r.status_code} en {url}; feed omitido.", file=sys.stderr)

            if i < len(FEEDS_ZONA) - 1:
                polite_sleep()
    return regs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Scraper Doomos — renta en Ciudad Nezahualcóyotl (franja de zona)"
    )
    parser.add_argument("--smoke", action="store_true", help="Prueba rápida de scrape_zona().")
    args = parser.parse_args()

    if args.smoke:
        filas = scrape_zona()
        print(f"[doomos] Total filas: {len(filas)}")
        if filas:
            print("Muestra:")
            for k, v in filas[0].items():
                print(f"  {k}: {v}")
        print(f"SMOKE_ROWS={len(filas)}")
    else:
        parser.print_help()


if __name__ == "__main__":
    _main()
