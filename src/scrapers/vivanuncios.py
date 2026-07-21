"""Scraper de renta (departamento/casa) en Nezahualcóyotl vía Vivanuncios.

Método: httpx + BeautifulSoup sobre HTML estático (sin Selenium).

Vivanuncios está tras Cloudflare. Con headers de navegador (`config.get_headers()`)
y **HTTP/1.1** responde 200 con el listado real embebido en el HTML. Con
HTTP/2 (`httpx.Client(http2=True, ...)`) el mismo request devuelve un
challenge gestionado de Cloudflare (403, `cf-mitigated: challenge`,
"Just a moment..."), reproducible de forma consistente en pruebas en vivo
(2026-07-21). No se intentó resolver el challenge (JS, cookies de sesión,
proxies, etc.) — solo se ajustó el parámetro de transporte `http2=False` del
mismo cliente httpx, manteniendo los mismos headers "browser-like" que ya usa
el resto del proyecto. Si en el futuro un feed regresa un challenge/interstitial
en vez de listados, se omite ese feed sin ningún intento adicional de evasión
(ver `scrape_zona`).

Selectores confirmados sobre HTML real (2026-07-21):
  - Card       : div[data-qa="posting PROPERTY"]
  - URL        : atributo `data-to-posting` del propio card (ruta relativa)
  - Precio     : [data-qa="POSTING_CARD_PRICE"] (texto "MN 9,000")
  - Features   : [data-qa="POSTING_CARD_FEATURES"] > span ("45 m² lote", "1 rec.",
                 "1 baño", "1 estac.")
  - Ubicación  : [data-qa="POSTING_CARD_LOCATION"]
  - Descripción: [data-qa="POSTING_CARD_DESCRIPTION"]
  - Publicador : img[data-qa="POSTING_CARD_PUBLISHER"] → atributo alt si existe
                 (en la práctica el alt observado es genérico, "logo publisher";
                 se extrae tal cual, no hay nombre de agencia real en el listado)
  - Teléfono   : gateado tras botón; NO se extrae (queda None)
"""
from __future__ import annotations

import argparse
import sys

import httpx
from bs4 import BeautifulSoup

from config import get_headers, polite_sleep
from utils import (
    clean_text,
    parse_banos,
    parse_estacionamientos,
    parse_m2,
    parse_precio,
    parse_recamaras,
)

FUENTE = "vivanuncios"
_BASE_URL = "https://www.vivanuncios.com.mx"

# ---------------------------------------------------------------------------
# Interfaz de zona (franja Alameda Oriente) — registros crudos, no canónicos
# ---------------------------------------------------------------------------

FEEDS_ZONA = [
    ("departamento", "https://www.vivanuncios.com.mx/s-departamentos-en-renta/nezahualcoyotl/v1c1300l10712p1"),
    ("casa", "https://www.vivanuncios.com.mx/s-casas-en-renta/nezahualcoyotl/v1c1299l10712p1"),
]


def _extraer_cards(soup: BeautifulSoup) -> list:
    """Devuelve todos los div[data-qa="posting PROPERTY"] de la sopa."""
    return soup.select('div[data-qa="posting PROPERTY"]')


def _extraer_precio(card) -> float | None:
    el = card.select_one('[data-qa="POSTING_CARD_PRICE"]')
    return parse_precio(el.get_text()) if el else None


def _extraer_url(card) -> str | None:
    ruta = card.get("data-to-posting")
    if not ruta:
        return None
    return _BASE_URL + ruta if ruta.startswith("/") else f"{_BASE_URL}/{ruta}"


def _extraer_titulo(card) -> str | None:
    el = card.select_one('[data-qa="POSTING_CARD_DESCRIPTION"]')
    return clean_text(el.get_text()) if el else None


def _extraer_ubicacion(card) -> str | None:
    el = card.select_one('[data-qa="POSTING_CARD_LOCATION"]')
    return clean_text(el.get_text()) if el else None


def _extraer_publicado_por(card) -> str | None:
    el = card.select_one('img[data-qa="POSTING_CARD_PUBLISHER"]')
    if el is None:
        return None
    return clean_text(el.get("alt"))


def _extraer_features(card) -> dict:
    """
    Parsea [data-qa="POSTING_CARD_FEATURES"] > span para obtener:
      m2, recamaras, banos, estacionamientos.

    Patrones observados: "45 m² lote", "1 rec.", "1 baño", "1 estac.".
    """
    result: dict = {"m2": None, "recamaras": None, "banos": None, "estacionamientos": None}
    contenedor = card.select_one('[data-qa="POSTING_CARD_FEATURES"]')
    if contenedor is None:
        return result

    for span in contenedor.find_all("span"):
        txt = clean_text(span.get_text()) or ""
        txt_lower = txt.lower()

        if "m²" in txt or "m2" in txt_lower:
            result["m2"] = parse_m2(txt)
        elif "rec" in txt_lower:
            result["recamaras"] = parse_recamaras(txt)
        elif "baño" in txt_lower or "bano" in txt_lower:
            result["banos"] = parse_banos(txt)
        elif "estac" in txt_lower or "auto" in txt_lower or "cochera" in txt_lower:
            result["estacionamientos"] = parse_estacionamientos(txt)

    return result


def _card_a_crudo(card, tipo: str) -> dict | None:
    """Convierte un card de Vivanuncios al registro crudo del contrato de zona."""
    url = _extraer_url(card)
    if not url:
        return None
    precio = _extraer_precio(card)
    titulo = _extraer_titulo(card) or ""
    ubicacion = _extraer_ubicacion(card) or ""
    feats = _extraer_features(card)
    return {
        "precio": precio,
        "tipo_inmueble": tipo,
        "m2": feats["m2"],
        "recamaras": feats["recamaras"],
        "banos": feats["banos"],
        "estacionamientos": feats["estacionamientos"],
        "url": url,
        "publicado_por": _extraer_publicado_por(card),
        "telefono": None,  # gateado tras botón; no se extrae
        "texto": f"{titulo} {ubicacion} {url}",
        "fuente": FUENTE,
    }


def parse_zona_html(html: str, tipo: str = "departamento") -> list[dict]:
    """Parsea el HTML de un listado de zona y devuelve registros crudos."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for card in _extraer_cards(soup):
        reg = _card_a_crudo(card, tipo)
        if reg is not None:
            out.append(reg)
    return out


def scrape_zona() -> list[dict]:
    """Descarga los feeds de la franja Alameda Oriente y devuelve registros crudos.

    Un feed que falle (error de red o challenge/interstitial en vez de
    listados) se omite sin abortar los demás.
    """
    regs: list[dict] = []
    with httpx.Client(http2=False, follow_redirects=True, timeout=25) as client:
        for i, (tipo, url) in enumerate(FEEDS_ZONA):
            try:
                r = client.get(url, headers=get_headers())
            except Exception as exc:
                print(f"[vivanuncios] ERROR al pedir {url}: {exc}", file=sys.stderr)
                r = None

            if r is not None and r.status_code == 200 and "posting PROPERTY" in r.text:
                regs.extend(parse_zona_html(r.text, tipo))
            elif r is not None:
                print(
                    f"[vivanuncios] AVISO: status {r.status_code} o challenge en {url}; feed omitido.",
                    file=sys.stderr,
                )

            if i < len(FEEDS_ZONA) - 1:
                polite_sleep()
    return regs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Scraper Vivanuncios — renta en Nezahualcóyotl (franja de zona)"
    )
    parser.add_argument("--smoke", action="store_true", help="Prueba rápida de scrape_zona().")
    args = parser.parse_args()

    if args.smoke:
        filas = scrape_zona()
        print(f"[vivanuncios] Total filas: {len(filas)}")
        if filas:
            print("Muestra:")
            for k, v in filas[0].items():
                print(f"  {k}: {v}")
        print(f"SMOKE_ROWS={len(filas)}")
    else:
        parser.print_help()


if __name__ == "__main__":
    _main()
