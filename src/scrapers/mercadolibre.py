"""Scraper de MercadoLibre Inmuebles — departamentos en renta CDMX por alcaldía.

Estrategia: Selenium con stealth Chrome. MercadoLibre renderiza la página con
React y embebe los datos de cada tarjeta (polycard) en JSON dentro del HTML.
Se extrae ese JSON mediante expresiones regulares sobre page_source.

Paginación: offsets en la URL con el patrón _Desde_{n}_NoIndex_True;
48 resultados por página (offsets: 0→sin sufijo, 49, 97, 145 …).

Uso:
    python scraper_mercadolibre.py --smoke   # Solo Benito Juárez, máx 2 págs.
    python scraper_mercadolibre.py --full    # Todas las alcaldías, escribe CSV.
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import random
import re
import sys
import time

# ── Silenciar logs ruidosos de webdriver-manager y selenium ─────────────────
logging.getLogger("WDM").setLevel(logging.ERROR)
logging.getLogger("selenium").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
os.environ.setdefault("WDM_LOG", "0")
os.environ.setdefault("WDM_LOG_LEVEL", "0")
os.environ.setdefault("WDM_PRINT_FIRST_LINE", "False")

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

sys.path.insert(0, os.path.dirname(__file__))
from config import (
    ALCALDIAS,
    ALCALDIAS_CANONICAS,
    MELI_RENTA,
    SELENIUM_ARGS,
    USER_AGENTS,
    polite_sleep,
)
from normaliza import COLUMNAS_CANONICAS, a_canonico, guarda_csv
from utils import parse_precio, parse_m2, parse_recamaras, parse_banos, parse_estacionamientos

# ── Constantes ────────────────────────────────────────────────────────────────
FUENTE = "mercadolibre"
# 48 resultados por página; el offset de la segunda página arranca en 49.
ITEMS_POR_PAGINA = 48
# Espera máxima (segundos) para que el contenedor de resultados aparezca.
WAIT_TIMEOUT = 15
# Selector CSS del contenedor principal de resultados (usado solo para sincronía).
SELECTOR_RESULTS = "ol.ui-search-layout, section.ui-search-results"


# ── Construcción de driver ────────────────────────────────────────────────────

def _build_driver() -> webdriver.Chrome:
    """Crea un driver Chrome con opciones stealth tal como se especificó."""
    o = Options()
    for a in SELENIUM_ARGS:
        o.add_argument(a)
    o.add_experimental_option("excludeSwitches", ["enable-automation"])
    o.add_experimental_option("useAutomationExtension", False)
    o.add_argument("user-agent=" + random.choice(USER_AGENTS))

    service = Service(ChromeDriverManager().install())
    d = webdriver.Chrome(service=service, options=o)
    d.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {"source": "Object.defineProperty(navigator,'webdriver',{get:()=>undefined})"},
    )
    return d


# ── Extracción desde page_source ──────────────────────────────────────────────

def _url_normalizada(raw: str) -> str:
    """Convierte la URL cruda (con \\u002F) a URL completa con https://."""
    url = raw.replace("\\u002F", "/").replace("/", "/")
    if not url.startswith("http"):
        url = "https://" + url
    # Quitar fragmento de tracking
    url = url.split("#")[0]
    return url


def _parsear_atributos(textos: list[str]) -> dict:
    """Mapea la lista de atributos de un polycard a campos del esquema."""
    resultado: dict = {}
    for txt in textos:
        txt_lower = txt.lower()
        if "recámara" in txt_lower or "recamara" in txt_lower:
            resultado["recamaras"] = parse_recamaras(txt)
        elif "baño" in txt_lower or "bano" in txt_lower:
            resultado["banos"] = parse_banos(txt)
        elif "m²" in txt_lower or "m2" in txt_lower:
            resultado["m2"] = parse_m2(txt)
        elif "estacionamiento" in txt_lower or "garage" in txt_lower or "cajón" in txt_lower:
            resultado["estacionamientos"] = parse_estacionamientos(txt)
    return resultado


def _extraer_polycards(page_source: str) -> list[dict]:
    """
    Extrae datos crudos de cada tarjeta usando regex sobre el JSON embebido.

    MercadoLibre incrusta los datos de cada 'polycard' directamente en el HTML
    como texto JSON dentro de un componente React. No hay etiquetas HTML con
    clases CSS en el DOM accesible via BeautifulSoup porque las clases están
    en atributos JSX serializados.

    Patrones usados:
        - ID: "id":"MLMxxxxxxx"
        - URL: "url":"departamento.mercadolibre..."
        - Precio: "current_price":{"value":N
        - Atributos: "attributes_list":{"separator":"...","texts":[...]
    """
    # Extraer IDs (orden de aparición)
    ids = re.findall(r'"id":"(MLM\d+)"', page_source)
    ids = list(dict.fromkeys(ids))  # deduplicar preservando orden

    # Extraer URLs
    urls_raw = re.findall(
        r'"id":"MLM\d+","url":"([^"]+)"', page_source
    )
    urls = [_url_normalizada(u) for u in urls_raw]

    # Extraer precios
    precios_raw = re.findall(
        r'"current_price":\{"value":(\d+)', page_source
    )

    # Extraer atributos
    attrs_raw = re.findall(
        r'"attributes_list":\{"separator":"[^"]+","texts":\[([^\]]+)\]',
        page_source,
    )

    n = min(len(ids), len(urls), len(precios_raw))
    if n == 0:
        return []

    registros: list[dict] = []
    for i in range(n):
        precio = parse_precio(precios_raw[i]) if i < len(precios_raw) else None
        atributos: dict = {}
        if i < len(attrs_raw):
            # attrs_raw[i] es algo como: '"2 recámaras","2 baños","69 m²"'
            # Parsear lista JSON-like
            try:
                textos = json.loads("[" + attrs_raw[i] + "]")
            except json.JSONDecodeError:
                # fallback: dividir por coma+comilla
                textos = re.findall(r'"([^"]+)"', attrs_raw[i])
            atributos = _parsear_atributos(textos)

        reg: dict = {
            "precio": precio,
            "tipo_inmueble": "departamento",
            "url": urls[i] if i < len(urls) else None,
            **atributos,
        }
        registros.append(reg)

    return registros


# ── Carga de página con reintentos ────────────────────────────────────────────

def _cargar_pagina(driver: webdriver.Chrome, url: str, reintentos: int = 2) -> bool:
    """Carga la URL y espera hasta que el contenido de resultados esté presente."""
    for intento in range(1, reintentos + 2):
        try:
            driver.get(url)
            # Esperar a que el número de resultados aparezca en el título o
            # a que existan elementos de tipo polycard en el JSON embebido.
            # Usamos un wait explícito sobre el <title> que contiene el conteo.
            WebDriverWait(driver, WAIT_TIMEOUT).until(
                lambda d: "departamento" in d.title.lower()
                or len(re.findall(r'"id":"MLM\d+"', d.page_source)) > 0
            )
            return True
        except Exception as exc:
            if intento <= reintentos:
                time.sleep(3 * intento)
            else:
                print(f"    [WARN] No se pudo cargar {url}: {exc}", file=sys.stderr)
    return False


# ── Paginación ────────────────────────────────────────────────────────────────

def _url_pagina(base_url: str, pagina: int) -> str:
    """Construye la URL de la página n (1-indexed).

    Página 1: URL base sin sufijo de offset.
    Página 2+: URL base + '_Desde_{offset}_NoIndex_True'
    donde offset = (pagina - 1) * ITEMS_POR_PAGINA + 1
    """
    if pagina <= 1:
        return base_url
    offset = (pagina - 1) * ITEMS_POR_PAGINA + 1
    # Insertar el sufijo antes del '?' o al final de la ruta
    url = base_url.rstrip("/")
    return f"{url}/_Desde_{offset}_NoIndex_True"


# ── API pública ───────────────────────────────────────────────────────────────

def scrape_alcaldia(
    driver: webdriver.Chrome,
    nombre_canonico: str,
    max_paginas: int = 3,
) -> list[dict]:
    """Raspa hasta max_paginas de departamentos en renta para una alcaldía.

    Parámetros
    ----------
    driver:
        Instancia de Chrome WebDriver ya inicializada (reusable).
    nombre_canonico:
        Nombre canónico de la alcaldía (key en ALCALDIAS de config.py).
    max_paginas:
        Número máximo de páginas a raspar (cada página tiene ~48 resultados).

    Retorna
    -------
    Lista de dicts en esquema canónico listos para guardar en CSV.
    """
    slug = ALCALDIAS.get(nombre_canonico)
    if not slug:
        print(f"[WARN] Alcaldía desconocida: {nombre_canonico}", file=sys.stderr)
        return []

    base_url = MELI_RENTA.format(slug=slug)
    filas: list[dict] = []
    paginas_vacias = 0

    for pagina in range(1, max_paginas + 1):
        url = _url_pagina(base_url, pagina)
        ok = _cargar_pagina(driver, url)
        if not ok:
            paginas_vacias += 1
            if paginas_vacias >= 2:
                break
            continue

        registros = _extraer_polycards(driver.page_source)
        if not registros:
            paginas_vacias += 1
            if paginas_vacias >= 2:
                break
        else:
            paginas_vacias = 0
            for reg in registros:
                fila = a_canonico(reg, FUENTE, nombre_canonico)
                filas.append(fila)

        if pagina < max_paginas:
            polite_sleep()

    return filas


def scrape_todas(
    max_paginas: int = 3,
    alcaldias: list[str] | None = None,
) -> list[dict]:
    """Raspa todas (o un subconjunto de) las alcaldías y devuelve todas las filas.

    Crea el driver internamente y lo cierra en un bloque finally.

    Parámetros
    ----------
    max_paginas:
        Páginas a raspar por alcaldía.
    alcaldias:
        Lista de nombres canónicos a raspar. None = todas las 16 alcaldías.

    Retorna
    -------
    Lista de dicts en esquema canónico.
    """
    nombres = alcaldias if alcaldias is not None else ALCALDIAS_CANONICAS
    todas_filas: list[dict] = []
    driver = _build_driver()
    try:
        for i, nombre in enumerate(nombres, 1):
            print(f"[{i}/{len(nombres)}] Raspando: {nombre} …", flush=True)
            t0 = time.time()
            filas = scrape_alcaldia(driver, nombre, max_paginas=max_paginas)
            dt = time.time() - t0
            print(f"    → {len(filas)} registros en {dt:.1f}s", flush=True)
            todas_filas.extend(filas)
            if i < len(nombres):
                polite_sleep()
    finally:
        driver.quit()

    return todas_filas


# ── CLI ───────────────────────────────────────────────────────────────────────

def _cli() -> None:
    parser = argparse.ArgumentParser(
        description="Scraper MercadoLibre — departamentos en renta CDMX."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--smoke",
        action="store_true",
        help="Modo smoke: solo Benito Juárez, máx 2 páginas.",
    )
    mode.add_argument(
        "--full",
        action="store_true",
        help="Modo full: todas las alcaldías → CSV en ../data/raw/mercadolibre.csv",
    )
    args = parser.parse_args()

    if args.smoke:
        print("=== SMOKE TEST — Benito Juárez ===")
        filas = scrape_todas(max_paginas=2, alcaldias=["Benito Juárez"])
        con_precio = [f for f in filas if f.get("precio") is not None]
        print(f"\nTotal registros : {len(filas)}")
        print(f"Con precio      : {len(con_precio)}")
        if filas:
            print("\nMuestras (2 primeros registros):")
            for f in filas[:2]:
                print(" ", {k: v for k, v in f.items() if v is not None})
        print(f"\nSMOKE_ROWS={len(filas)}")
        return

    # Modo full (--full o sin argumentos)
    print("=== SCRAPING COMPLETO — 16 alcaldías ===")
    filas = scrape_todas(max_paginas=3)
    ruta = os.path.join(
        os.path.dirname(__file__), "..", "data", "raw", "mercadolibre.csv"
    )
    ruta = os.path.normpath(ruta)
    n = guarda_csv(filas, ruta)
    print(f"\nTotal filas escritas: {n}")
    print(f"Archivo: {ruta}")


if __name__ == "__main__":
    _cli()
