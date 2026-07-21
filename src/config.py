"""Configuración compartida del Proyecto 3 — scraping de renta de inmuebles en CDMX.

Contiene el toolkit anti-bloqueo (User-Agents, headers, delays), el catálogo
canónico de las 16 alcaldías de la Ciudad de México y las plantillas de URL por
portal. Todos los scrapers importan desde aquí para garantizar consistencia.
"""
from __future__ import annotations

import random
import time

ESTADO = "Ciudad de México"

# --- Toolkit anti-bloqueo (libreta UserAgentCustomization.ipynb) -------------
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.4 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
]

# Delay aleatorio entre requests (segundos). Cortesía + evasión de rate-limit.
DELAY_MIN = 2.5
DELAY_MAX = 5.0


def get_headers() -> dict[str, str]:
    """Headers de navegador realistas con User-Agent rotado aleatoriamente."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "es-MX,es;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": "https://www.google.com/",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "cross-site",
        "Sec-Fetch-User": "?1",
        "Connection": "keep-alive",
    }


def polite_sleep() -> None:
    """Pausa aleatoria entre peticiones para no saturar al servidor."""
    time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))


# --- Argumentos stealth para Selenium ---------------------------------------
SELENIUM_ARGS = [
    "--headless=new",
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--window-size=1920,1080",
    "--lang=es-MX",
    "--disable-gpu",
]

# --- Catálogo canónico de las 16 alcaldías de la CDMX ------------------------
# Nombre canónico -> slug kebab-case usado por la mayoría de portales.
ALCALDIAS: dict[str, str] = {
    "Álvaro Obregón": "alvaro-obregon",
    "Azcapotzalco": "azcapotzalco",
    "Benito Juárez": "benito-juarez",
    "Coyoacán": "coyoacan",
    "Cuajimalpa": "cuajimalpa",
    "Cuauhtémoc": "cuauhtemoc",
    "Gustavo A. Madero": "gustavo-a-madero",
    "Iztacalco": "iztacalco",
    "Iztapalapa": "iztapalapa",
    "Magdalena Contreras": "magdalena-contreras",
    "Miguel Hidalgo": "miguel-hidalgo",
    "Milpa Alta": "milpa-alta",
    "Tláhuac": "tlahuac",
    "Tlalpan": "tlalpan",
    "Venustiano Carranza": "venustiano-carranza",
    "Xochimilco": "xochimilco",
}

# Lista canónica de nombres (para validar/estandarizar en la limpieza).
ALCALDIAS_CANONICAS = list(ALCALDIAS.keys())

# --- Plantillas de URL por portal -------------------------------------------
# Cada scraper construye sus URLs a partir del slug de la alcaldía. La paginación
# concreta (parámetro de página/offset) la maneja cada scraper.

# Lamudi (BeautifulSoup + httpx). Probado: 200 OK, listings en HTML estático.
LAMUDI_BASE = "https://www.lamudi.com.mx"
LAMUDI_RENTA = LAMUDI_BASE + "/distrito-federal/{slug}/for-rent/"

# Nuroa (BeautifulSoup + httpx). Agregador. Probado: itemtype microdata + JSON-LD.
NUROA_BASE = "https://www.nuroa.com.mx"
NUROA_RENTA = NUROA_BASE + "/renta-departamento-{slug}-distrito-federal"

# MercadoLibre Inmuebles (Selenium). Probado: ~493 anuncios/página vía stealth.
MELI_BASE = "https://inmuebles.mercadolibre.com.mx"
MELI_RENTA = MELI_BASE + "/departamentos/renta/distrito-federal/{slug}/"

# Vivanuncios (Selenium; 403 en HTTP plano). Slug de localidad por descubrir.
VIVANUNCIOS_BASE = "https://www.vivanuncios.com.mx"
VIVANUNCIOS_RENTA = VIVANUNCIOS_BASE + "/s-renta-inmuebles/distrito-federal/{slug}/v1c1097l1008p1"
