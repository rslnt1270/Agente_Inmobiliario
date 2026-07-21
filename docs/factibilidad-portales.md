# Factibilidad de portales — scraping de renta (franja Alameda Oriente / Nezahualcóyotl)

Veredictos de portales probados en vivo para el pipeline de zona (Task 6–8).
"Integrado" significa que el portal expone `scrape_zona()` registrado en
`src/scrapers/__init__.py::SCRAPERS_ZONA` con el contrato de 11 claves.

| Portal | Método | Veredicto | Notas |
|--------|--------|-----------|-------|
| Lamudi | httpx+BS4 | ✅ | integrado |
| Nuroa | httpx+BS4 | ✅ | integrado |
| MercadoLibre | Selenium | ✅ | integrado |
| Doomos | httpx + JSON RSC | ✅ | integrado; expone `contact_phone` |
| Casas y Terrenos | httpx+BS4 | ✅ pero sin inventario en la zona | no integrado (resultados fallback de otras alcaldías) |
| Nestoria | — | ❌ | 401 Access Denied (gate de borde) |
| Properati MX | — | ❌ | DNS muerto (.mx discontinuado) |
| Point2Homes | — | ❌ | 410, sin inventario MX |
| Inmuebles24 | — | ❌ | DataDome 403 |
| Propiedades.com | — | ❌ | challenge anti-bot |
| icasas / vivastreet / segundamano | — | ❌ | muertos/redirigen |
| Vivanuncios | httpx+BS4 (`data-qa`) | ❌ | Cloudflare managed challenge bajo HTTP/2 con headers de navegador; solo responde si se degrada el fingerprint a HTTP/1.1 = evasión, fuera de alcance |

## Notas de integración (Task 8)

### Vivanuncios (bloqueado, no integrado)

Confirmado en vivo (2026-07-21): con `httpx.Client(http2=True, ...)` +
`config.get_headers()` (el mismo cliente que usan `nuroa`/`lamudi`), Vivanuncios
responde **403 con un challenge gestionado de Cloudflare** ("Just a moment...",
header `cf-mitigated: challenge`), de forma consistente en múltiples intentos.
Con el mismo cliente y los mismos headers pero `http2=False` (HTTP/1.1),
responde **200** con el HTML de listados real. Es decir, el portal solo cede
contenido si se degrada deliberadamente el fingerprint de transporte para
esquivar el challenge — eso es evasión de una protección anti-bot, fuera del
alcance permitido del proyecto (regla: solo se scrapea lo que el sitio sirve
sin circunvenir un challenge). Por eso Vivanuncios se removió de
`SCRAPERS_ZONA` y queda reclasificado como ❌ bloqueado en la tabla de arriba,
pese a que técnicamente el HTML era parseable con `data-qa`.

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
