# Documento de Requerimientos - PWA Gestión de Departamentos (Proyecto "CClean")

## 1. Resumen Ejecutivo y Visión del Proyecto
Desarrollo de una Aplicación Web Progresiva (PWA) para optimizar la logística, administración y mantenimiento de un portafolio inicial de 5 departamentos. Actualmente, el modelo de negocio principal es el arrendamiento corporativo a través de contratos con CEMEX. El sistema debe resolver las necesidades operativas actuales (calendario de limpiezas, mantenimiento, control financiero y obligaciones fiscales) y estar preparado para escalar a un modelo de rentas a corto plazo (Airbnb) en un horizonte de 2 años, así como la incorporación inmediata de una sexta propiedad bajo el esquema de Airbnb.

## 2. Modelos de Propiedad y Negocio Actual
El sistema debe poder clasificar y manejar la lógica financiera de los siguientes tipos de propiedades:
- **Propios (2 departamentos):** Ingreso íntegro, gastos de mantenimiento y limpieza a cargo de la administración.
- **Administrados a Terceros (1 departamento):** La dueña es externa. Se cobra comisión por administración; se gestiona la limpieza y su pago respectivo.
- **Subarrendados (2 departamentos):** Se paga renta mensual a un propietario, se invirtió en mobiliario, y se subarrenda a CEMEX.
- **Nuevos/Corto Plazo (1 departamento - Próximamente):** Subarrendado, pero operado directamente para Airbnb.

## 3. Perfiles de Usuario (Control de Acceso Basado en Roles)
- **Responsables de la Administración (Mamá y Usuario):** Tienen acceso al *Dashboard* central.
  - **Mamá (Administradora Principal):** Acceso total. Gestión financiera, facturación ante CEMEX, SAT, calendario maestro, asignación de limpiezas y visibilidad completa del control de calidad.
  - **Usuario (Co-Administrador/Mantenimiento):** Acceso a calendario maestro, gestión y cierre de tickets de desperfectos, alertas del hardware (y4ga-bot) y logística de "Experiencias".
- **Personal de Limpieza (Colaboradoras):** Perfil de "solo ejecución". Únicamente ven su calendario de tareas del día/semana. **No tienen acceso a finanzas, facturación ni contratos.** Utilizan la app estrictamente para ver a dónde ir, hacer *Check-in/Check-out* fotográfico y reportar insumos.
- **Personal Externo de Mantenimiento:** *(Fase 2)* Perfil opcional para recibir tickets de reparación.

## 4. Requerimientos Funcionales

### 4.1. Gestión Operativa y Calendario (Limpieza)
- **Programación de Limpiezas:** Sistema de calendario unificado. Capacidad de programar recurrentemente 2 limpiezas quincenales por departamento (4 al mes) por defecto para el contrato CEMEX.
- **Asignación de Personal:** Asignar limpiezas a colaboradoras específicas o a la Administradora Principal.
- **Módulo de Supervisión Avanzada e Integración Hardware (Proyecto "y4ga-bot"):**
  - **Cámaras Corporales (Bodycams):** Integración con cámaras portátiles basadas en ESP32 usadas por el personal de limpieza. El objetivo es salvaguardar las pertenencias e integridad de los inquilinos (2 a 3 ingenieros de CEMEX por departamento) y tener evidencia del cumplimiento de las reglas.
  - **Check-in / Check-out:** Registro rápido desde el celular (geolocalizado) con botones de "Iniciar Limpieza" y "Terminar Limpieza".
  - **Checklists Fotográficos:** Cuestionario rápido al finalizar (ej. ¿Se sacó la basura?, ¿Se lavaron sábanas?) con carga de fotografía del trabajo terminado como evidencia.
  - **Reporte de Insumos:** Sección para reportar insumos faltantes.
- **Escalabilidad para nuevas contrataciones:** Diseñado para que el nuevo personal de limpieza sea monitoreado de manera estricta pero sin fricción tecnológica, eliminando la dependencia de la supervisión presencial.

### 4.2. Mantenimiento y Desperfectos
- **Creación de Tickets:** Permitir a administradores o personal de limpieza reportar desperfectos con fotografías y nivel de urgencia.
- **Seguimiento:** Estados del ticket (Reportado, En Proceso, Resuelto).
- **Costos de Reparación:** Asignar el costo de la reparación o la factura del profesional externo (plomería, albañilería) a los egresos del departamento correspondiente.

### 4.3. Gestión Financiera y Fiscal
- **Registro de Ingresos:** Registro del pago mensual fijo de CEMEX por departamento (y futuros ingresos variables de Airbnb).
- **Registro de Egresos:**
  - Pago de servicios (luz, agua, internet, gas).
  - Pago de rentas de los departamentos subarrendados.
  - Pago de nómina/servicios a las colaboradoras de limpieza.
  - Pago a propietarios de departamentos bajo administración (restando la comisión).
- **Control Fiscal y Facturación (Notificaciones):**
  - Alertas automáticas programables para emitir las facturas mensuales en el portal de CEMEX.
  - Alertas o notificaciones en fechas clave del mes para la recopilación de facturas de gastos y presentación de declaraciones ante el SAT.

### 4.4. Integración Airbnb (Actual) y "Experiencias"
Dado que actualmente **un departamento** ya opera bajo el esquema de Airbnb y su dinámica es conocida:
- **Sincronización Airbnb:** La PWA debe contemplar la administración paralela (o sincronización de calendarios vía iCal/API) para este departamento específico, ya que la gestión directa de huéspedes se hace desde la app de Airbnb.
- **Módulo de "Experiencias" Airbnb:**
  - Creación de un apartado independiente a los departamentos para gestionar la logística de "Experiencias" (recorridos turísticos y servicios).
  - Permitir llevar el control del calendario, cupos e insumos necesarios para estas experiencias una vez que el anuncio sea aprobado por la plataforma.
- **Transición a Futuro (2 años):** La base de datos y la lógica de programación deben estar estructuradas para que, al concluir los contratos con CEMEX, el resto de los departamentos puedan migrar sin problemas a este modelo de limpieza variable (bajo demanda por salida de huésped) y reserva a corto plazo.

### 4.5. Dashboard de Gestión: Calendario y Notificaciones
Diseñado exclusivamente para los **Responsables (Mamá y Usuario)**, será el centro de control logístico:
- **Calendario Maestro Unificado:**
  - Vista visual interactiva de los 5 departamentos (propios, subarrendados, comisión), el departamento Airbnb y el módulo de Experiencias.
  - Diferenciación visual (colores/iconos) entre: Limpiezas CEMEX (fijas), Limpiezas Airbnb (dinámicas), Mantenimientos (reparaciones), y Experiencias agendadas.
  - Filtros para ver la agenda global o la de una colaboradora de limpieza en específico.
- **Centro de Notificaciones y Alertas:**
  - **Alertas Operativas:** Notificaciones push en tiempo real cuando una colaboradora inicia o finaliza un servicio (con acceso rápido a la foto de evidencia), o si reportan falta de insumos (jabón, papel).
  - **Alertas Administrativas/Fiscales:** Recordatorios automáticos programados (ej. "Día de subir facturas al portal CEMEX", "Día límite para recopilar comprobantes de gastos para el SAT").
  - **Alertas de Mantenimiento:** Avisos instantáneos de nuevos tickets de desperfectos o alertas de seguridad del hardware *y4ga-bot*.

## 5. Requerimientos No Funcionales
- **Plataforma:** PWA (Progressive Web App). Debe ser instalable desde el navegador en iOS y Android, y funcionar fluidamente en navegadores de escritorio.
- **Interfaz (UX/UI):** Especial atención a la simplicidad para el rol de *Personal de Limpieza*. Botones grandes, uso de íconos y flujos intuitivos sin exceso de texto.
- **Sistema de Notificaciones:** Notificaciones Push (si el navegador lo permite), o integración con un bot de WhatsApp / Email para las alertas críticas (SAT, Facturas, Emergencias de Mantenimiento).
- **Seguridad y Privacidad:** Aislamiento estricto de datos financieros. El personal de limpieza no debe tener acceso a contratos, montos de cobro de CEMEX ni rentas.

## 6. Propuestas de Mejoras Logísticas (Valor Agregado)
1. **Inventario de Blancos e Insumos:** Un control sencillo de cuántas sábanas, toallas y productos de limpieza hay en cada departamento, alertando cuando es necesario hacer compras.
2. **Cálculo Automático de Rentabilidad:** Un dashboard que muestre automáticamente la ganancia neta por departamento después de restar renta (si aplica), servicios, limpiezas y mantenimiento, separando los que son negocio propio de los que son subarriendo o comisión.
3. **Portal o Exportación para Propietarios Externos:** Un reporte PDF mensual automático para la dueña del departamento administrado, justificando los descuentos por limpieza/servicios y mostrando su ganancia final.
