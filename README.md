# Agente Inmobiliario

Buscador de renta de inmuebles en la Ciudad de México, enfocado en la franja
Alameda Oriente con un baseline citywide para comparar precios.

Autor: Roman Yair Ortega

## Cómo ejecutar

```bash
PYTHONPATH=src python -m zona.run_zona
```

## Esquema del CSV maestro

`data/clean/inmuebles_limpio.csv`

| Columna | Descripción |
|---|---|
| `precio` | Precio de renta mensual (MXN) |
| `tipo_inmueble` | Tipo de inmueble (departamento, casa, oficina, local, etc.) |
| `alcaldia` | Alcaldía de la Ciudad de México |
| `estado` | Estado (siempre "Ciudad de México") |
| `m2` | Superficie en metros cuadrados |
| `recamaras` | Número de recámaras |
| `banos` | Número de baños |
| `estacionamientos` | Número de estacionamientos |
| `url` | URL del anuncio original |
| `fuente` | Portal de origen (lamudi, nuroa, mercadolibre, vivanuncios) |
| `precio_por_m2` | Precio de renta dividido entre `m2` |
