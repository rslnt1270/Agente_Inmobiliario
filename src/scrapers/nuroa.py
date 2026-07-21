"""Scraper de renta de departamentos en CDMX vía Nuroa.

Método: httpx (http2=True) + BeautifulSoup. Sin Selenium.

URL base: https://www.nuroa.com.mx/renta-departamentos/departamento-{slug}
Paginación: sufijo ?page={n}
Microdata: div[itemtype*="Product"] (29 cards/página en páginas con suficientes resultados)

Selectores confirmados:
  - Precio  : span[itemprop="price"] → atributo content (numérico)
  - Dirección: .nu_address_text (texto; se usa para inferir alcaldía)
  - Título  : a.nu_adlink (texto)
  - Features: ul.nu_features > li (habitaciones, baños, m², garage)
  - URL     : a.nu_adlink → href (enlace adform de Nuroa)

Nota: Tláhuac devuelve 404 y se omite con advertencia.
"""
from __future__ import annotations

import argparse
import re
import sys
import urllib.parse

import httpx
from bs4 import BeautifulSoup

# Importar contratos compartidos (mismo directorio)
from config import ALCALDIAS, ALCALDIAS_CANONICAS, get_headers, polite_sleep
from normaliza import COLUMNAS_CANONICAS, a_canonico, guarda_csv
from utils import (
    clean_text,
    normaliza_alcaldia,
    parse_banos,
    parse_estacionamientos,
    parse_m2,
    parse_precio,
    parse_recamaras,
)

# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------
FUENTE = "nuroa"
_BASE_URL = "https://www.nuroa.com.mx/renta-departamentos/departamento-{slug}"

# Tláhuac no tiene URL funcional en Nuroa; se omite.
_SLUGS_SIN_PAGINA = {"tlahuac"}


# ---------------------------------------------------------------------------
# Helpers de extracción
# ---------------------------------------------------------------------------

def _construir_url(slug: str, pagina: int) -> str:
    """Devuelve la URL de listado para el slug y número de página dados."""
    base = _BASE_URL.format(slug=slug)
    if pagina <= 1:
        return base
    return f"{base}?page={pagina}"


def _extraer_cards(soup: BeautifulSoup) -> list:
    """Devuelve todos los div[itemtype*='Product'] de la sopa."""
    return soup.find_all(attrs={"itemtype": lambda v: v and "Product" in v})


def _extraer_precio(card) -> float | None:
    """Lee el atributo content de span[itemprop='price']."""
    precio_span = card.find("span", attrs={"itemprop": "price"})
    if precio_span is None:
        return None
    content = precio_span.get("content")
    return parse_precio(content)


def _extraer_url(card) -> str | None:
    """Devuelve el href del enlace adform (a.nu_adlink)."""
    a = card.find("a", class_="nu_adlink")
    return a.get("href") if a else None


def _extraer_titulo(card) -> str | None:
    """Texto del enlace principal del anuncio."""
    a = card.find("a", class_="nu_adlink")
    return clean_text(a.get_text()) if a else None


def _extraer_direccion(card) -> str | None:
    """Texto de .nu_address_text."""
    div = card.find(class_="nu_address_text")
    return clean_text(div.get_text()) if div else None


def _extraer_features(card) -> dict:
    """
    Parsea ul.nu_features > li para obtener:
      habitaciones, banos, m2, estacionamientos.

    Patrones reconocidos:
      - "N habitación(es)"  -> recamaras
      - "N baño(s)"         -> banos
      - "N m²" (sin MXN)   -> m2
      - "garage"            -> estacionamientos = 1
    """
    result: dict = {
        "recamaras": None,
        "banos": None,
        "m2": None,
        "estacionamientos": None,
    }
    feats_ul = card.find("ul", class_="nu_features")
    if feats_ul is None:
        return result

    for li in feats_ul.find_all("li"):
        txt = clean_text(li.get_text()) or ""
        txt_lower = txt.lower()

        if "habitaci" in txt_lower or "recámara" in txt_lower or "recamara" in txt_lower:
            result["recamaras"] = parse_recamaras(txt)
        elif "baño" in txt_lower or "bano" in txt_lower:
            result["banos"] = parse_banos(txt)
        elif "m²" in txt and "MXN" not in txt and "mxn" not in txt_lower:
            result["m2"] = parse_m2(txt)
        elif "garage" in txt_lower or "estacionamiento" in txt_lower or "parking" in txt_lower:
            # Nuroa muestra "garage" sin número; asumimos 1 lugar
            num = parse_estacionamientos(txt)
            result["estacionamientos"] = num if num is not None else 1

    return result


def _parsear_card(card, nombre_alcaldia: str) -> dict | None:
    """
    Convierte un div[itemtype*='Product'] al esquema canónico.
    Devuelve None si falla la extracción (try/except).
    """
    try:
        precio = _extraer_precio(card)
        url = _extraer_url(card)
        titulo = _extraer_titulo(card)
        direccion = _extraer_direccion(card)
        feats = _extraer_features(card)

        # Inferir tipo_inmueble desde título/URL (default: departamento)
        tipo = "departamento"
        if titulo:
            titulo_lower = titulo.lower()
            for kw, t in [
                ("casa", "casa"),
                ("local", "local"),
                ("oficina", "oficina"),
                ("estudio", "estudio"),
                ("loft", "loft"),
            ]:
                if kw in titulo_lower:
                    tipo = t
                    break

        # Alcaldía: intentar desde la dirección del anuncio; fallback al contexto
        alcaldia_anuncio = normaliza_alcaldia(direccion) if direccion else None

        registro = {
            "precio": precio,
            "tipo_inmueble": tipo,
            "alcaldia": alcaldia_anuncio,  # a_canonico usa fallback si es None
            "m2": feats["m2"],
            "recamaras": feats["recamaras"],
            "banos": feats["banos"],
            "estacionamientos": feats["estacionamientos"],
            "url": url,
        }
        return a_canonico(registro, FUENTE, nombre_alcaldia)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Función principal por alcaldía
# ---------------------------------------------------------------------------

def scrape_alcaldia(nombre_canonico: str, max_paginas: int = 3) -> list[dict]:
    """
    Raspa hasta max_paginas páginas de Nuroa para la alcaldía indicada.

    Parámetros
    ----------
    nombre_canonico : str
        Nombre canónico de la alcaldía (p. ej. "Benito Juárez").
    max_paginas : int
        Límite de páginas a recuperar.

    Devuelve
    --------
    list[dict]
        Lista de registros en esquema canónico.
    """
    slug = ALCALDIAS.get(nombre_canonico)
    if slug is None:
        print(f"[nuroa] AVISO: alcaldía desconocida '{nombre_canonico}'", file=sys.stderr)
        return []

    if slug in _SLUGS_SIN_PAGINA:
        print(
            f"[nuroa] AVISO: '{nombre_canonico}' ({slug}) no tiene URL válida en Nuroa; omitida.",
            file=sys.stderr,
        )
        return []

    resultados: list[dict] = []
    ids_vistos: set[str] = set()  # deduplicación por id de card

    with httpx.Client(http2=True, follow_redirects=True, timeout=25) as client:
        for pagina in range(1, max_paginas + 1):
            url = _construir_url(slug, pagina)
            try:
                resp = client.get(url, headers=get_headers())
            except Exception as exc:
                print(f"[nuroa] ERROR al pedir {url}: {exc}", file=sys.stderr)
                break

            if resp.status_code == 404:
                # Sin resultados para esta alcaldía/página
                if pagina == 1:
                    print(
                        f"[nuroa] AVISO: 404 en página 1 para '{nombre_canonico}' ({url})",
                        file=sys.stderr,
                    )
                break

            if resp.status_code != 200:
                print(
                    f"[nuroa] AVISO: status {resp.status_code} en {url}",
                    file=sys.stderr,
                )
                break

            soup = BeautifulSoup(resp.text, "html.parser")
            cards = _extraer_cards(soup)

            if not cards:
                break  # Página vacía

            nuevas = 0
            for card in cards:
                card_id = card.get("id", "")
                if card_id in ids_vistos:
                    continue
                ids_vistos.add(card_id)

                fila = _parsear_card(card, nombre_canonico)
                if fila is not None:
                    resultados.append(fila)
                    nuevas += 1

            print(
                f"[nuroa] {nombre_canonico} pág {pagina}: {len(cards)} cards, "
                f"{nuevas} nuevas -> total {len(resultados)}",
                file=sys.stderr,
            )

            # Comprobar si hay página siguiente
            next_link = soup.find("link", rel="next")
            if next_link is None:
                break

            if pagina < max_paginas:
                polite_sleep()

    return resultados


# ---------------------------------------------------------------------------
# Scraper completo
# ---------------------------------------------------------------------------

def scrape_todas(
    max_paginas: int = 3,
    alcaldias: list[str] | None = None,
) -> list[dict]:
    """
    Raspa todas las alcaldías (o la lista indicada) y devuelve los registros.

    Parámetros
    ----------
    max_paginas : int
        Páginas por alcaldía.
    alcaldias : list[str] | None
        Subconjunto de nombres canónicos. None = las 16.
    """
    objetivo = alcaldias if alcaldias is not None else ALCALDIAS_CANONICAS
    total: list[dict] = []

    for nombre in objetivo:
        filas = scrape_alcaldia(nombre, max_paginas=max_paginas)
        total.extend(filas)
        if nombre != objetivo[-1]:
            polite_sleep()

    return total


# ---------------------------------------------------------------------------
# Interfaz de zona (franja Alameda Oriente) — registros crudos, no canónicos
# ---------------------------------------------------------------------------

FEEDS_ZONA = [
    "https://www.nuroa.com.mx/renta-departamentos/departamento-nezahualcoyotl",
    "https://www.nuroa.com.mx/renta-casas/casa-nezahualcoyotl",
]


def _card_a_crudo(card) -> dict | None:
    """Convierte un card de Nuroa al registro crudo del contrato de zona."""
    precio = _extraer_precio(card)
    url = _extraer_url(card)
    titulo = _extraer_titulo(card) or ""
    direccion = _extraer_direccion(card) or ""
    feats = _extraer_features(card)
    if not url:
        return None
    tipo = "casa" if "casa" in titulo.lower() else "departamento"
    return {
        "precio": precio,
        "tipo_inmueble": tipo,
        "m2": feats["m2"],
        "recamaras": feats["recamaras"],
        "banos": feats["banos"],
        "estacionamientos": feats["estacionamientos"],
        "url": url,
        "publicado_por": None,   # Nuroa no expone publicador en el listado
        "telefono": None,        # ni teléfono público
        "texto": f"{titulo} {direccion} {url}",
        "fuente": "nuroa",
    }


def parse_zona_html(html: str) -> list[dict]:
    """Parsea el HTML de un listado de zona y devuelve registros crudos."""
    soup = BeautifulSoup(html, "html.parser")
    out = []
    for card in _extraer_cards(soup):
        reg = _card_a_crudo(card)
        if reg is not None:
            out.append(reg)
    return out


def scrape_zona() -> list[dict]:
    """Descarga los feeds de la franja Alameda Oriente y devuelve registros crudos."""
    regs: list[dict] = []
    with httpx.Client(http2=True, follow_redirects=True, timeout=25) as client:
        for i, url in enumerate(FEEDS_ZONA):
            try:
                r = client.get(url, headers=get_headers())
            except Exception:
                continue
            if r.status_code == 200:
                regs.extend(parse_zona_html(r.text))
            if i < len(FEEDS_ZONA) - 1:
                polite_sleep()
    return regs


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _main() -> None:
    parser = argparse.ArgumentParser(
        description="Scraper Nuroa — renta de departamentos en CDMX"
    )
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument(
        "--smoke",
        action="store_true",
        help="Prueba rápida: solo Benito Juárez, máx 2 páginas.",
    )
    modo.add_argument(
        "--full",
        action="store_true",
        help="Scrape completo de las 16 alcaldías y guarda CSV.",
    )
    args = parser.parse_args()

    if args.smoke:
        print("[nuroa] Modo SMOKE — Benito Juárez, 2 páginas")
        filas = scrape_alcaldia("Benito Juárez", max_paginas=2)
        con_precio = [f for f in filas if f.get("precio") is not None]
        print(f"\nTotal filas: {len(filas)}")
        print(f"Filas con precio no nulo: {len(con_precio)}")
        if filas:
            print("\nMuestra 1:")
            for k, v in filas[0].items():
                print(f"  {k}: {v}")
        if len(filas) > 1:
            print("\nMuestra 2:")
            for k, v in filas[1].items():
                print(f"  {k}: {v}")
        print(f"\nSMOKE_ROWS={len(filas)}")

    elif args.full:
        print("[nuroa] Modo FULL — scrapeando las 16 alcaldías")
        filas = scrape_todas(max_paginas=3)
        ruta = "../data/raw/nuroa.csv"
        n = guarda_csv(filas, ruta)
        print(f"[nuroa] CSV guardado en {ruta} con {n} filas.")

    else:
        parser.print_help()


if __name__ == "__main__":
    _main()
