# Factibilidad de portales — scraping de renta (franja Alameda Oriente / Nezahualcóyotl)

Veredictos de portales probados en vivo para el pipeline de zona (Task 6–8).
"Integrado" significa que el portal expone `scrape_zona()` registrado en
`src/scrapers/__init__.py::SCRAPERS_ZONA` con el contrato de 11 claves.

| Portal | Método | Veredicto | Notas |
|--------|--------|-----------|-------|
| Lamudi | httpx+BS4 | ✅ | integrado |
| Nuroa | httpx+BS4 | ✅ | integrado |
| MercadoLibre | Selenium | ✅ | integrado |
| Vivanuncios | httpx+BS4 (`data-qa`) | ✅ | integrado; teléfono gateado (no se extrae); requiere `httpx.Client(http2=False, ...)` — con HTTP/2 el mismo request dispara un challenge gestionado de Cloudflare (ver detalle abajo) |
| Doomos | httpx + JSON RSC | ✅ | integrado; expone `contact_phone` |
| Casas y Terrenos | httpx+BS4 | ✅ pero sin inventario en la zona | no integrado (resultados fallback de otras alcaldías) |
| Nestoria | — | ❌ | 401 Access Denied (gate de borde) |
| Properati MX | — | ❌ | DNS muerto (.mx discontinuado) |
| Point2Homes | — | ❌ | 410, sin inventario MX |
| Inmuebles24 | — | ❌ | DataDome 403 |
| Propiedades.com | — | ❌ | challenge anti-bot |
| icasas / vivastreet / segundamano | — | ❌ | muertos/redirigen |

## Notas de integración (Task 8)

### Vivanuncios

Confirmado en vivo (2026-07-21): con `httpx.Client(http2=True, ...)` +
`config.get_headers()` (el mismo cliente que usan `nuroa`/`lamudi`), Vivanuncios
responde **403 con un challenge gestionado de Cloudflare** ("Just a moment...",
header `cf-mitigated: challenge`), de forma consistente en múltiples intentos.
Con el mismo cliente y los mismos headers pero `http2=False` (HTTP/1.1),
responde **200** con el HTML de listados real. No se intentó resolver el
challenge (sin ejecución de JS, sin cookies de sesión de terceros, sin
proxies) — el ajuste fue únicamente el parámetro de transporte del propio
cliente httpx del proyecto. `scrape_zona()` usa `http2=False`; si en el
futuro un feed vuelve a devolver un challenge/interstitial en vez de
listados, se omite ese feed (try/except por feed, sin evasión adicional).

El campo `publicado_por` se extrae del `alt` de `img[data-qa="POSTING_CARD_PUBLISHER"]`
cuando existe; en la práctica ese `alt` es un texto genérico ("logo publisher"),
no el nombre real de la agencia — se deja tal cual porque es lo único
disponible en el listado. `telefono` queda `None` (gateado tras botón).

### Doomos

Los listados no están en el HTML estático como markup — viajan como blobs de
texto JSON-escapado dentro de `self.__next_f.push([1, "..."])` (stream RSC de
Next.js). Extracción implementada en `src/scrapers/doomos.py`:
1. Regex "escape-aware" que captura el string de cada `push([1, "..."])`
   respetando comillas escapadas internas.
2. Un `json.loads('"' + s + '"')` por blob para revertir el escapado JSON
   estándar (\", \r\n, etc.) y recuperar el texto embebido real.
3. Sobre ese texto, un escaneo balanceado de llaves (respetando strings/escapes)
   que localiza objetos `{"id": ...}` y los valida con `json.loads`, quedándose
   solo con los que tienen `listing_type` y `price` (i.e. son anuncios).

Confirmado en vivo: 3 anuncios en `/renta/departamentos/ciudad-nezahualcoyotl`,
1 anuncio en `/renta/casas/ciudad-nezahualcoyotl` — este último es el glitch
conocido: una casa en **venta** por $2,700,000 mal etiquetada con
`listing_type.name = "Renta"`. El scraper no filtra esto (fiel a lo que hay
en el feed); el filtro de precio ≤ $18,000/mes aguas abajo
(`zona/filtros.py`) descarta ese registro del pipeline de zona.

`telefono` se puebla desde `contact_phone` (alimenta el canal de contacto).
`publicado_por` queda `None` (no hay campo de agencia en el listado). La URL
de detalle no viene como `href` explícito en el payload; se construye
`https://www.doomos.com.mx/propiedad/<slug>`, patrón verificado en vivo (200,
contenido coincide con precio/título del listado de origen).
