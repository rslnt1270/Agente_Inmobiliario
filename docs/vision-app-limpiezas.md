# Visión — App de registro de limpiezas (Subproyecto B)

> **Estado: VISIÓN / futuro.** Fuera del alcance de la fase A (migración + buscador
> de la franja Alameda Oriente). Este documento solo fija la idea; su construcción
> tendrá su propio ciclo **spec → plan → implementación**, igual que la fase A.

## Idea

Una aplicación para **registrar y dar seguimiento a las limpiezas** de los
departamentos que se gestionan en renta —vía **Airbnb** o **alquiler
independiente**— dentro de la zona que el buscador ya inventaría.

El buscador (fase A) responde *"qué propiedades hay y cómo contactarlas"*. Esta app
responde lo siguiente en el ciclo operativo: *"una vez que administro una propiedad,
¿quién la limpió, cuándo, en qué estado quedó y cuánto costó?"*.

## Qué registraría (borrador, no comprometido)

| Campo | Descripción |
|---|---|
| `propiedad` | Identificador de la unidad (dirección/colonia; puede enlazar al inventario de la zona). |
| `fecha` | Fecha/hora de la limpieza. |
| `responsable` | Persona o cuadrilla que ejecutó la limpieza. |
| `estatus` | Programada / en curso / terminada / con incidencias. |
| `costo` | Costo de la limpieza. |
| `canal` | Origen de la estancia: Airbnb / alquiler independiente. |
| `notas` | Observaciones (daños, faltantes, tiempos). |

## Relación con la fase A

- El **inventario de la franja** (`data/clean/zona_alameda_oriente.csv`) puede servir
  como catálogo inicial de propiedades a las que, si se administran, se les asocian
  limpiezas.
- Comparten el enfoque geográfico (zona Alameda Oriente), pero son **subsistemas
  independientes**: el buscador es extracción/consolidación de datos públicos; la app
  de limpiezas es registro operativo de un negocio.

## Preguntas abiertas (para el brainstorming de B, cuando toque)

- ¿App web, móvil, o una hoja/servicio ligero? ¿Un solo usuario o cuadrilla?
- ¿Persistencia local o en la nube? ¿Multiusuario?
- ¿Integra calendarios de reservas (Airbnb iCal) o es captura manual?
- ¿Reportes (costo por propiedad/mes, frecuencia de limpieza)?

Nada de lo anterior se decide aquí. Se documenta para no perder la visión.
