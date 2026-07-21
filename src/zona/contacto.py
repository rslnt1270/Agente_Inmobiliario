"""Canal de contacto público de un anuncio.

Solo compone lo que el portal expone en abierto: teléfono si es público,
publicador si aparece, y siempre la URL del anuncio como canal base (el
contacto ocurre por el formulario/chat del propio portal). No accede a datos
gateados.
"""
from __future__ import annotations


def construir_canal(
    fuente: str,
    url: str,
    publicado_por: str | None = None,
    telefono: str | None = None,
) -> str:
    partes: list[str] = []
    if telefono:
        partes.append(f"tel:{telefono}")
    if publicado_por:
        partes.append(publicado_por.strip())
    if not telefono:
        partes.append(f"vía portal ({fuente})")
    partes.append(url)
    return " | ".join(partes)
