"""Scraper de renta de inmuebles en Lamudi México por alcaldía (CDMX).

Método: httpx (HTTP/2) + BeautifulSoup sobre HTML estático.
Selectores verificados contra HTML real descargado de Lamudi (2026-06).

Selectores clave:
  - Contenedor de anuncio : [data-test="normal-listing"]
  - Título                : .snippet__content__title
  - Precio                : .snippet__content__price
  - Ubicación             : [data-test="snippet-content-location"]
  - Recámaras             : [data-test="bedrooms-value"]
  - Baños                 : [data-test="full-bathrooms-value"]
  - Área / m²             : [data-test="area-value"]
  - Estacionamiento       : [data-test="amenity-value"].car_park
  - Paginación            : ?page=N (href en [data-test="pagination-next"])
"""
from __future__ import annotations

import argparse
import logging
import re
import sys

import httpx
from bs4 import BeautifulSoup

from config import (
    ALCALDIAS,
    ALCALDIAS_CANONICAS,
    LAMUDI_BASE,
    LAMUDI_RENTA,
    get_headers,
    polite_sleep,
)
from normaliza import a_canonico, guarda_csv
from utils import (
    clean_text,
    normaliza_alcaldia,
    parse_banos,
    parse_estacionamientos,
    parse_int,
    parse_m2,
    parse_precio,
    parse_recamaras,
)

# ---------------------------------------------------------------------------
# Constante de fuente — identificador canónico del portal
# ---------------------------------------------------------------------------
FUENTE = "lamudi"

# Logger del módulo
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Mapa de palabras clave en título -> tipo canónico de inmueble
# ---------------------------------------------------------------------------
_TIPO_KEYWORDS: list[tuple[str, str]] = [
    ("departamento", "departamento"),
    ("depto", "departamento"),
    ("casa", "casa"),
    ("local", "local"),
    ("oficina", "oficina"),
    ("bodega", "bodega"),
    ("terreno", "terreno"),
    ("cuarto", "cuarto"),
    ("estudio", "estudio"),
    ("penthouse", "penthouse"),
    ("loft", "loft"),
]


def _inferir_tipo(titulo: str, url: str) -> str:
    """Infiere el tipo de inmueble a partir del título y/o la URL.

    Recorre las palabras clave en orden de prioridad (departamento primero).
    Devuelve 'departamento' como valor por defecto.
    """
    texto = (titulo + " " + url).lower()
    for keyword, tipo in _TIPO_KEYWORDS:
        if keyword in texto:
            return tipo
    return "departamento"


def _construir_url_pagina(slug: str, pagina: int) -> str:
    """Construye la URL para una alcaldía y número de página dados.

    Página 1 no lleva parámetro (URL limpia); páginas 2+ usan ?page=N.
    """
    base = LAMUDI_RENTA.format(slug=slug)
    if pagina <= 1:
        return base
    return f"{base}?page={pagina}"


def _parsear_precio(texto_precio: str | None) -> float | None:
    """Extrae el valor numérico del precio, filtrando monedas distintas a MXN.

    Lamudi puede mostrar precios en USD. Solo se aceptan precios en MXN
    (incluidos los que solo tienen '$' sin especificar moneda).
    """
    if not texto_precio:
        return None
    texto = texto_precio.upper()
    # Si el texto contiene 'USD' explícito, descartar (moneda extranjera)
    if "USD" in texto and "MXN" not in texto:
        return None
    return parse_precio(texto_precio)


def _extraer_anuncio(card: BeautifulSoup, nombre_canonico: str) -> dict | None:
    """Extrae los campos de un anuncio individual (card HTML) de Lamudi.

    Devuelve un registro crudo (aún sin pasar por a_canonico) o None si el
    anuncio no tiene datos mínimos utilizables.
    """
    # --- URL del anuncio ---
    a_tag = card.find("a", href=True)
    if not a_tag:
        return None
    href = a_tag["href"]
    url = (LAMUDI_BASE + href) if href.startswith("/") else href

    # --- Título ---
    title_el = card.find(class_="snippet__content__title")
    titulo = clean_text(title_el.get_text()) if title_el else ""

    # --- Tipo de inmueble ---
    tipo_inmueble = _inferir_tipo(titulo or "", url)

    # --- Precio ---
    price_el = card.find(class_="snippet__content__price")
    precio_raw = clean_text(price_el.get_text()) if price_el else None
    precio = _parsear_precio(precio_raw)

    # --- Ubicación / alcaldía ---
    loc_el = card.find(attrs={"data-test": "snippet-content-location"})
    ubicacion = clean_text(loc_el.get_text()) if loc_el else None
    # Intentar normalizar la alcaldía desde la ubicación del anuncio;
    # si no se puede, usar el nombre_canonico del contexto de scraping.
    alcaldia_detectada = normaliza_alcaldia(ubicacion) if ubicacion else None
    alcaldia = alcaldia_detectada or nombre_canonico

    # --- Recámaras ---
    bed_el = card.find(attrs={"data-test": "bedrooms-value"})
    recamaras = parse_recamaras(bed_el.get_text() if bed_el else None)

    # --- Baños ---
    bath_el = card.find(attrs={"data-test": "full-bathrooms-value"})
    banos = parse_banos(bath_el.get_text() if bath_el else None)

    # --- Área (m²) ---
    # Nota: parse_m2 de utils.py trata la coma como separador decimal.
    # Para evitar que "1,100 m²" sea interpretado como 1.1, se elimina
    # la coma de miles antes de pasar el texto (ej. "1,100 m²" -> "1100 m²").
    area_el = card.find(attrs={"data-test": "area-value"})
    area_raw = area_el.get_text() if area_el else None
    if area_raw:
        # Quitar coma de miles solo cuando va entre dígitos (no es decimal)
        area_raw = re.sub(r"(\d),(\d{3})", r"\1\2", area_raw)
    m2 = parse_m2(area_raw)

    # --- Estacionamientos ---
    # El elemento [data-test="amenity-value"] puede representar distintas
    # amenidades (terraza, seguridad, estacionamiento...).
    # Solo extraemos estacionamientos cuando la clase CSS incluye "car_park".
    estacionamientos = None
    amenity_el = card.find(attrs={"data-test": "amenity-value"})
    if amenity_el:
        clases = amenity_el.get("class", [])
        if "car_park" in clases:
            estacionamientos = parse_estacionamientos(amenity_el.get_text())

    return {
        "url": url,
        "tipo_inmueble": tipo_inmueble,
        "precio": precio,
        "alcaldia": alcaldia,
        "m2": m2,
        "recamaras": recamaras,
        "banos": banos,
        "estacionamientos": estacionamientos,
        # Campos extra (ignorados por a_canonico) reutilizados por scrape_zona
        # para construir el texto de detección de colonia.
        "titulo": titulo,
        "ubicacion": ubicacion,
    }


def _descargar_pagina(url: str) -> BeautifulSoup | None:
    """Descarga una URL con httpx (HTTP/2) y devuelve el árbol BeautifulSoup.

    Devuelve None si la respuesta no es 200.
    """
    try:
        with httpx.Client(http2=True, follow_redirects=True, timeout=25) as client:
            respuesta = client.get(url, headers=get_headers())
    except httpx.RequestError as exc:
        log.warning("Error de red al descargar %s: %s", url, exc)
        return None

    if respuesta.status_code != 200:
        log.warning(
            "HTTP %s al descargar %s (body[:200]: %s)",
            respuesta.status_code,
            url,
            respuesta.text[:200],
        )
        return None

    return BeautifulSoup(respuesta.content, "html.parser")


def _hay_pagina_siguiente(soup: BeautifulSoup) -> bool:
    """Verifica si existe un enlace habilitado a la página siguiente."""
    next_el = soup.find(attrs={"data-test": "pagination-next"})
    if not next_el:
        return False
    # El enlace está deshabilitado cuando su href está vacío o la clase
    # incluye "disabled".
    href = next_el.get("href", "").strip()
    clases = next_el.get("class", [])
    return bool(href) and "disabled" not in clases


# ---------------------------------------------------------------------------
# API pública del módulo
# ---------------------------------------------------------------------------

def scrape_alcaldia(nombre_canonico: str, max_paginas: int = 3) -> list[dict]:
    """Scrapea los anuncios de renta de una alcaldía en Lamudi.

    Itera hasta `max_paginas` páginas de resultados. Aplica polite_sleep
    entre páginas para ser respetuoso con el servidor.

    Args:
        nombre_canonico: Nombre de la alcaldía según ALCALDIAS_CANONICAS
                         (ej. "Benito Juárez").
        max_paginas:     Límite máximo de páginas a scrapear por alcaldía.

    Returns:
        Lista de registros canónicos (dicts con COLUMNAS_CANONICAS).
    """
    if nombre_canonico not in ALCALDIAS:
        log.error("Alcaldía desconocida: %r. Valores válidos: %s", nombre_canonico, ALCALDIAS_CANONICAS)
        return []

    slug = ALCALDIAS[nombre_canonico]
    filas: list[dict] = []

    log.info("Scrapeando alcaldía '%s' (slug=%s, max_paginas=%d)", nombre_canonico, slug, max_paginas)

    for pagina in range(1, max_paginas + 1):
        url_pagina = _construir_url_pagina(slug, pagina)
        log.info("  Página %d/%d — %s", pagina, max_paginas, url_pagina)

        soup = _descargar_pagina(url_pagina)
        if soup is None:
            log.warning("  No se pudo descargar la página %d; abortando alcaldía.", pagina)
            break

        # Extraer todas las cards de anuncios normales
        cards = soup.find_all(attrs={"data-test": "normal-listing"})
        log.info("  Encontradas %d cards en página %d", len(cards), pagina)

        for card in cards:
            try:
                registro = _extraer_anuncio(card, nombre_canonico)
                if registro is None:
                    continue
                fila_canonica = a_canonico(registro, FUENTE, nombre_canonico)
                filas.append(fila_canonica)
            except Exception as exc:
                log.debug("Error procesando card (omitida): %s", exc)

        # Verificar si hay página siguiente antes de dormir
        if pagina < max_paginas and _hay_pagina_siguiente(soup):
            polite_sleep()
        else:
            # No hay más páginas o alcanzamos el límite
            break

    log.info("Alcaldía '%s': %d registros totales", nombre_canonico, len(filas))
    return filas


def scrape_todas(
    max_paginas: int = 3,
    alcaldias: list[str] | None = None,
) -> list[dict]:
    """Scrapea todas las alcaldías (o las especificadas) en Lamudi.

    Args:
        max_paginas: Límite de páginas por alcaldía.
        alcaldias:   Lista de nombres canónicos a scrapear. Si es None,
                     se recorren todas las 16 alcaldías de ALCALDIAS_CANONICAS.

    Returns:
        Lista consolidada de registros canónicos de todas las alcaldías.
    """
    objetivo = alcaldias if alcaldias is not None else ALCALDIAS_CANONICAS
    todas: list[dict] = []

    log.info("Scrapeando %d alcaldías con max_paginas=%d", len(objetivo), max_paginas)

    for nombre in objetivo:
        filas = scrape_alcaldia(nombre, max_paginas=max_paginas)
        todas.extend(filas)
        if nombre != objetivo[-1]:
            # Pausa cortés entre alcaldías
            polite_sleep()

    log.info("Total de registros obtenidos: %d", len(todas))
    return todas


# ---------------------------------------------------------------------------
# Interfaz de zona (franja Alameda Oriente) — registros crudos, no canónicos
# ---------------------------------------------------------------------------
# Nezahualcóyotl vive en Lamudi bajo "/mexico/..." (Edomex), no "/distrito-federal/".
# Las colonias de GAM (San Juan de Aragón, Campestre Aragón) sí resuelven en su URL
# propia sin redirigir a otro estado; en cambio los slugs de colonia de VC e
# Iztacalco (moctezuma, pantitlan...) chocan con topónimos homónimos de otros
# estados y Lamudi redirige mal (verificado en vivo) — por eso para esas dos
# alcaldías se usa el feed a nivel alcaldía completo (más ruido, pero correcto;
# zona/filtros.py se encarga de acotar a las colonias exactas vía `texto`).
# Nota: "venustiano-carranza" (slug de config.py) también redirige a Chiapas;
# el slug correcto de la alcaldía CDMX en Lamudi es "venustiano-carranza-1".
FEEDS_ZONA = [
    "https://www.lamudi.com.mx/mexico/nezahualcoyotl/for-rent/",
    "https://www.lamudi.com.mx/mexico/nezahualcoyotl/casa/for-rent/",
    "https://www.lamudi.com.mx/distrito-federal/gustavo-a-madero/san-juan-de-aragon/for-rent/",
    "https://www.lamudi.com.mx/distrito-federal/gustavo-a-madero/campestre-aragon/for-rent/",
    "https://www.lamudi.com.mx/distrito-federal/venustiano-carranza-1/for-rent/",
    "https://www.lamudi.com.mx/distrito-federal/iztacalco/for-rent/",
]

MAX_PAGINAS_ZONA = 2


def _url_zona_pagina(url_base: str, pagina: int) -> str:
    """Añade '?page=N' a un feed de zona ya completo (páginas 2+)."""
    if pagina <= 1:
        return url_base
    return f"{url_base}?page={pagina}"


def _anuncio_a_crudo(anuncio: dict) -> dict:
    """Mapea el dict de `_extraer_anuncio` al contrato crudo de zona (11 claves)."""
    titulo = anuncio.get("titulo") or ""
    ubicacion = anuncio.get("ubicacion") or ""
    url = anuncio.get("url") or ""
    return {
        "precio": anuncio.get("precio"),
        "tipo_inmueble": anuncio.get("tipo_inmueble") or "departamento",
        "m2": anuncio.get("m2"),
        "recamaras": anuncio.get("recamaras"),
        "banos": anuncio.get("banos"),
        "estacionamientos": anuncio.get("estacionamientos"),
        "url": url,
        "publicado_por": None,  # Lamudi no expone publicador en el listado
        "telefono": None,       # ni teléfono público
        "texto": f"{titulo} {ubicacion} {url}",
        "fuente": FUENTE,
    }


def scrape_zona(max_paginas: int = MAX_PAGINAS_ZONA) -> list[dict]:
    """Descarga los feeds de la franja Alameda Oriente y devuelve registros crudos.

    Reutiliza `_descargar_pagina`, `_extraer_anuncio` y `_hay_pagina_siguiente`
    (los mismos helpers que `scrape_alcaldia`), solo que sobre URLs de feed ya
    completas en vez de construidas a partir de un slug de alcaldía.
    """
    regs: list[dict] = []
    for i, url_base in enumerate(FEEDS_ZONA):
        for pagina in range(1, max_paginas + 1):
            url = _url_zona_pagina(url_base, pagina)
            soup = _descargar_pagina(url)
            if soup is None:
                break

            cards = soup.find_all(attrs={"data-test": "normal-listing"})
            if not cards:
                break

            for card in cards:
                try:
                    anuncio = _extraer_anuncio(card, "")
                    if anuncio is None:
                        continue
                    regs.append(_anuncio_a_crudo(anuncio))
                except Exception:
                    continue

            if pagina < max_paginas and _hay_pagina_siguiente(soup):
                polite_sleep()
            else:
                break

        if i < len(FEEDS_ZONA) - 1:
            polite_sleep()

    return regs


# ---------------------------------------------------------------------------
# Interfaz de línea de comandos (CLI)
# ---------------------------------------------------------------------------

def _cli() -> None:
    """Punto de entrada de la CLI. Modes: --smoke (prueba rápida) o --full."""
    parser = argparse.ArgumentParser(
        description="Scraper de renta de inmuebles en Lamudi MX por alcaldía."
    )
    grupo = parser.add_mutually_exclusive_group()
    grupo.add_argument(
        "--smoke",
        action="store_true",
        help="Modo prueba: scrapea solo Benito Juárez (máx 2 páginas) e imprime muestra.",
    )
    grupo.add_argument(
        "--full",
        action="store_true",
        help="Modo completo: scrapea las 16 alcaldías y guarda ../data/raw/lamudi.csv.",
    )
    args = parser.parse_args()

    if args.smoke:
        # --- Modo smoke test ---
        print("=== SMOKE TEST: Benito Juárez (máx 2 páginas) ===")
        filas = scrape_alcaldia("Benito Juárez", max_paginas=2)
        con_precio = [f for f in filas if f.get("precio") is not None]
        print(f"Total filas scraped  : {len(filas)}")
        print(f"Filas con precio     : {len(con_precio)}")

        print("\n--- Muestra de 2 filas ---")
        for fila in con_precio[:2]:
            print(fila)

        print(f"\nSMOKE_ROWS={len(con_precio)}")

        if len(con_precio) < 8:
            print(
                f"ADVERTENCIA: se obtuvieron solo {len(con_precio)} filas con precio "
                "(umbral mínimo: 8). Revisar selectores o bloqueo del sitio."
            )
            sys.exit(1)
        else:
            print("OK: umbral de 8 filas con precio alcanzado.")

    else:
        # --- Modo full (default) ---
        print("=== MODO FULL: scrapeando las 16 alcaldías ===")
        filas = scrape_todas(max_paginas=3)
        ruta_csv = "../data/raw/lamudi.csv"
        total = guarda_csv(filas, ruta_csv)
        print(f"Total de registros guardados en {ruta_csv}: {total}")


if __name__ == "__main__":
    _cli()
