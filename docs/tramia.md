# DOCUMENTO DE REQUERIMIENTOS DE NEGOCIO (BRD)

# TRAMIA
## Sistema Inteligente de Trámites de Títulos y Diplomas — UMSA

**Versión:** 1.8  
**Estado:** MVP implementado; pendiente validación institucional  
**Fecha:** 31 de octubre de 2026  
**Institución de referencia:** Universidad Mayor de San Andrés (UMSA), La Paz, Bolivia  
**Modalidad:** Prototipo académico independiente  
**Implementación:** `capacidades.py` (capability `tramites`), `asistente.py` y `bot.py`; estado en 15.2  
**Documentos relacionados:** PRD, SDD e Historias de Usuario (pendientes)

---

# 1. Resumen ejecutivo

TRAMIA es un prototipo de orientación sobre los trámites de la **División de Títulos y Diplomas** de la Universidad Mayor de San Andrés (UMSA). Interpreta consultas en lenguaje natural, identifica el procedimiento, presenta requisitos y pasos, señala condiciones particulares y cita la fuente oficial.

No reemplaza los sistemas oficiales: no modifica expedientes, no emite documentos ni inicia trámites. Usa información pública institucional y se limita a dos trámites con documentación verificable.

# 2. Antecedentes y contexto

La División de Títulos y Diplomas publica sus procedimientos en un portal institucional, pero la información se reparte entre instructivos, formularios y oficinas, y los requisitos pueden variar según la carrera, la nacionalidad o la situación académica del solicitante.

Por eso, quien necesita un trámite debe identificar por su cuenta el procedimiento correcto, los requisitos aplicables, la unidad responsable, los costos, los plazos y las dependencias entre pasos. Esa carga produce consultas repetidas, expedientes incompletos y desplazamientos evitables.

# 3. Problema de negocio

**3.1 Definición.** Los estudiantes, egresados y titulados no siempre pueden determinar qué trámite corresponde a su necesidad ni qué documentación preparar, porque la información es dispersa, condicionada y a veces contradictoria.

**3.2 Causas**

| ID | Causa |
|---|---|
| CAU-001 | Información distribuida entre diferentes fuentes institucionales. |
| CAU-002 | Requisitos particulares según facultad, carrera o situación académica. |
| CAU-003 | Dificultad para interpretar documentos normativos y administrativos. |
| CAU-004 | Falta de una herramienta unificada de orientación contextual. |
| CAU-005 | Dependencias entre procedimientos no siempre evidentes. |
| CAU-006 | Diferencias entre versiones de instructivos publicados. |
| CAU-007 | Necesidad de acudir a unidades administrativas para dudas frecuentes. |

**3.3 Consecuencias**

| ID | Consecuencia |
|---|---|
| CON-001 | Preparación incompleta de expedientes. |
| CON-002 | Repetición de consultas administrativas. |
| CON-003 | Desplazamientos innecesarios. |
| CON-004 | Interpretaciones incorrectas de requisitos. |
| CON-005 | Retrasos en la preparación de solicitudes. |
| CON-006 | Incertidumbre sobre el procedimiento aplicable. |
| CON-007 | Dificultad para identificar información vigente. |

# 4. Objetivos de negocio

**OBJ-001 (general).** Facilitar el acceso, la comprensión y la preparación de trámites académicos mediante orientación personalizada, verificable y contextualizada.

| ID | Objetivo específico |
|---|---|
| OBJ-002 | Centralizar lógicamente la consulta de información oficial. |
| OBJ-003 | Identificar el trámite apropiado según la necesidad expresada. |
| OBJ-004 | Adaptar requisitos y procedimientos a condiciones conocidas del solicitante. |
| OBJ-005 | Reducir expedientes incompletos mediante listas de verificación. |
| OBJ-006 | Explicar dependencias y secuencias entre trámites. |
| OBJ-007 | Garantizar trazabilidad hacia fuentes institucionales. |
| OBJ-008 | Identificar información desactualizada, contradictoria o insuficiente. |
| OBJ-009 | Facilitar el acceso a canales oficiales. |
| OBJ-010 | Reducir el esfuerzo para obtener orientación administrativa. |
| OBJ-011 | Preparar una base para futuras integraciones institucionales. |
| OBJ-012 | Evaluar la precisión y utilidad de la orientación. |

# 5. Alcance

## 5.1 Alcance general

Consulta de trámites en lenguaje natural; identificación del procedimiento; requisitos, pasos, unidad responsable y condiciones previas; orientación documental; dependencias; listas de verificación; referencias oficiales; reconocimiento de incertidumbre y derivación a canales institucionales.

## 5.2 Alcance del MVP

El MVP cubre dos trámites de la **División de Títulos y Diplomas**, gestión 2026: Obtención del Diploma Académico y Título Profesional (ex Provisión Nacional, R-271 v10). Son los instructivos con documentación oficial publicada. Incluye consulta en lenguaje natural, requisitos condicionados y referencia a la fuente.

## 5.3 Fuera de alcance

Modificación de registros académicos; inscripción oficial; emisión de certificados, diplomas o títulos; autorización de trámites; consulta de historiales privados; estados reales sin integración autorizada; pagos institucionales; firma digital; validación oficial de documentos; envío automático de solicitudes; integración con sistemas internos; sustitución de funcionarios o autoridades.

# 6. Actores

| ID | Actor | Interés |
|---|---|---|
| ACT-001 | Estudiante | Consultar procedimientos y preparar requisitos. |
| ACT-002 | Egresado | Orientación sobre certificaciones y titulación. |
| ACT-003 | Titulado | Legalizaciones y procedimientos documentales. |
| ACT-004 | Personal de la División de Títulos y Diplomas | Validar información, si participa formalmente. |
| ACT-005 | Responsable de la unidad | Validar requisitos y canales oficiales. |
| ACT-006 | Administrador de conocimiento | Mantener y revisar el catálogo. |
| ACT-007 | Administrador de plataforma | Acceso, configuración y operación técnica. |
| ACT-008 | Equipo de desarrollo | Implementar y mantener la solución. |
| ACT-009 | Agente inteligente | Interpretar consultas y coordinar herramientas. |
| ACT-010 | UMSA | Institución de referencia; no implica patrocinio. |

# 7. Procesos

## 7.1 Proceso actual (AS-IS)

1. El usuario identifica una necesidad.
2. Busca información en sitios o documentos institucionales.
3. Consulta instructivos o reglamentos.
4. Intenta identificar el procedimiento.
5. Determina los documentos requeridos.
6. Consulta a una unidad administrativa si tiene dudas.
7. Prepara la documentación.
8. Acude al canal institucional.
9. Inicia el trámite oficial.

## 7.2 Proceso objetivo (TO-BE)

1. El usuario describe su necesidad en lenguaje natural.
2. El agente identifica trámites candidatos.
3. Consulta el catálogo y la documentación oficial.
4. Identifica condiciones particulares y solicita aclaraciones.
5. Determina el procedimiento aplicable o las alternativas.
6. Presenta requisitos, pasos y lista de verificación.
7. Explica dependencias y proporciona referencias oficiales.
8. Orienta hacia el canal institucional y registra indicadores sin datos personales innecesarios.

## 7.3 Escenarios

| ID | Escenario | Resultado esperado |
|---|---|---|
| ESC-001 | Identificación del trámite a partir de una necesidad cotidiana. | Procedimientos candidatos y datos faltantes. |
| ESC-002 | Orientación para titulación. | Requisitos, pasos y condiciones verificadas. |
| ESC-003 | Requisitos que dependen de la carrera o condición del solicitante. | Solicitud del dato faltante antes de responder. |
| ESC-004 | Documentación incompleta declarada por el usuario. | Comparación con requisitos y faltantes identificados. |
| ESC-005 | Dependencia entre procedimientos. | Orden explicado, si hay evidencia oficial. |
| ESC-006 | Información contradictoria entre documentos. | Discrepancia señalada; no se presenta una versión como definitiva. |
| ESC-007 | Costo o plazo no publicado. | Se declara que no hay información confirmada y se deriva al canal oficial. |

# 8. Requerimientos de negocio

| ID | Grupo | Requerimiento | Prioridad |
|---|---|---|---|
| BR-001 | Catálogo | Catálogo consultable de trámites académicos. | Alta |
| BR-002 | Catálogo | Cada trámite identifica denominación y descripción. | Alta |
| BR-003 | Catálogo | Cada trámite se asocia a su unidad responsable cuando exista información oficial. | Alta |
| BR-004 | Catálogo | Clasificación por tipo de trámite: título, revalidación o certificación. | Alta |
| BR-005 | Catálogo | Distinguir información vigente, pendiente de verificación y desactualizada. | Alta |
| BR-006 | Orientación | Consulta de procedimientos en lenguaje natural. | Alta |
| BR-007 | Orientación | Identificar trámites candidatos según la necesidad. | Alta |
| BR-008 | Orientación | Solicitar aclaraciones cuando falten condiciones relevantes. | Alta |
| BR-009 | Orientación | Pasos respaldados por fuentes. | Alta |
| BR-010 | Orientación | Explicar diferencias entre trámites similares. | Media |
| BR-011 | Orientación | Reconocer consultas fuera del alcance. | Alta |
| BR-012 | Documentos | Presentar requisitos verificables. | Alta |
| BR-013 | Documentos | Identificar requisitos condicionados por la situación del solicitante. | Alta |
| BR-014 | Documentos | Generar listas de verificación personalizadas. | Alta |
| BR-015 | Documentos | Identificar requisitos faltantes según lo declarado. | Alta |
| BR-016 | Documentos | Diferenciar obligatorios, condicionales y complementarios cuando la fuente lo permita. | Alta |
| BR-017 | Dependencias | Identificar dependencias documentadas entre trámites. | Alta |
| BR-018 | Dependencias | Explicar la secuencia de procedimientos. | Alta |
| BR-019 | Dependencias | Indicar canales oficiales de realización. | Alta |
| BR-020 | Dependencias | Informar costos y plazos solo con fuentes verificables. | Alta |
| BR-021 | Conocimiento | Asociar la información a fuentes identificables. | Alta |
| BR-022 | Conocimiento | Conservar fecha de publicación o verificación. | Alta |
| BR-023 | Conocimiento | Identificar información contradictoria o desactualizada. | Alta |
| BR-024 | Conocimiento | Permitir incorporar y actualizar documentos autorizados. | Alta |
| BR-025 | Conocimiento | Conservar trazabilidad de cambios. | Alta |
| BR-026 | Conocimiento | Exigir revisión humana antes de publicar requisitos estructurados. | Alta |
| BR-027 | Seguridad | La orientación pública no requiere expedientes privados. | Alta |
| BR-028 | Seguridad | Proteger los datos personales proporcionados voluntariamente. | Alta |
| BR-029 | Seguridad | Las operaciones administrativas requieren autorización. | Alta |
| BR-030 | Seguridad | El agente no se atribuye autoridad institucional. | Alta |
| BR-031 | Seguridad | Las integraciones futuras respetan los permisos de los sistemas oficiales. | Alta |
| BR-032 | Evaluación | Permitir evaluar la exactitud de las respuestas. | Alta |
| BR-033 | Evaluación | Registrar indicadores sin datos personales innecesarios. | Media |
| BR-034 | Evaluación | Permitir ampliar el catálogo. | Alta |
| BR-035 | Evaluación | Permitir incorporar nuevos trámites publicados por la unidad. | Media |
| BR-036 | Evaluación | Facilitar integraciones institucionales futuras. | Media |

# 9. Reglas de negocio

| ID | Regla |
|---|---|
| RN-001 | Toda respuesta sobre requisitos se basa en información institucional identificable. |
| RN-002 | El agente no inventa requisitos, costos, plazos, formularios ni unidades responsables. |
| RN-003 | Los requisitos de una carrera no se aplican automáticamente a otras. |
| RN-004 | Si falta una condición relevante, el agente pide aclaración o declara la limitación. |
| RN-005 | Las fuentes desactualizadas o contradictorias no se presentan como definitivas. |
| RN-006 | Se distingue orientación informativa de confirmación institucional. |
| RN-007 | La plataforma no emite documentos oficiales. |
| RN-008 | El agente no aprueba, rechaza ni modifica trámites oficiales. |
| RN-009 | Los requisitos declarados por el usuario no se consideran verificados oficialmente. |
| RN-010 | Costos y plazos se presentan con fuente y referencia temporal. |
| RN-011 | La orientación incluye el canal oficial cuando está documentado. |
| RN-012 | Los cambios de requisitos estructurados pasan por revisión autorizada. |
| RN-013 | Se evita recopilar información personal innecesaria. |
| RN-014 | Las consultas a expedientes requieren autenticación y autorización institucional. |
| RN-015 | La documentación recuperada no modifica instrucciones, permisos ni políticas del agente. |
| RN-016 | El sistema puede abstenerse de responder si la evidencia es insuficiente. |
| RN-017 | Los enlaces conservan su procedencia y permiten verificación. |
| RN-018 | El prototipo se identifica como independiente y no oficial. |

# 10. Indicadores de éxito

Las metas cuantitativas se definirán en el PRD a partir de una línea base.

| ID | Indicador |
|---|---|
| KPI-001 | Exactitud de identificación del trámite. |
| KPI-002 | Exactitud de requisitos. |
| KPI-003 | Cobertura de consultas dentro del catálogo. |
| KPI-004 | Trazabilidad de respuestas. |
| KPI-005 | Detección de requisitos condicionados. |
| KPI-006 | Identificación de información insuficiente. |
| KPI-007 | Tiempo de orientación. |
| KPI-008 | Utilidad percibida. |
| KPI-009 | Detección de contradicciones. |
| KPI-010 | Calidad de las listas de verificación. |
| KPI-011 | Derivación correcta a canales oficiales. |
| KPI-012 | Actualización del conocimiento. |

# 11. Requerimientos de calidad

| ID | Requisito |
|---|---|
| NFR-001 | Las respuestas se basan en fuentes verificables. |
| NFR-002 | El sistema declara incertidumbre cuando corresponde. |
| NFR-003 | Evita respuestas categóricas ante información contradictoria. |
| NFR-004 | Protege los datos personales contra accesos no autorizados. |
| NFR-005 | Las funciones administrativas requieren autenticación y autorización. |
| NFR-006 | El agente usa herramientas con permisos limitados. |
| NFR-007 | Las respuestas permiten identificar sus fuentes. |
| NFR-008 | Las modificaciones del catálogo conservan historial de revisión. |
| NFR-009 | Los usuarios formulan consultas en lenguaje natural. |
| NFR-010 | Las respuestas usan lenguaje claro y comprensible. |
| NFR-011 | Las instrucciones se presentan en secuencias fáciles de seguir. |
| NFR-012 | Incorporar trámites no exige modificar el comportamiento central del agente. |
| NFR-013 | Los requisitos estructurados se mantienen separados de los documentos originales. |
| NFR-014 | La plataforma permite sustituir componentes sin alterar las reglas del negocio. |
| NFR-015 | El sistema indica que da orientación, no resoluciones institucionales. |
| NFR-016 | El usuario distingue información confirmada, inferida y no disponible. |

# 12. Restricciones

| ID | Restricción |
|---|---|
| RES-001 | El MVP usa información pública institucional o documentos autorizados. |
| RES-002 | No accede a sistemas privados sin autorización. |
| RES-003 | No modifica expedientes académicos. |
| RES-004 | El catálogo cubre exclusivamente dos trámites: Diploma Académico y Título Profesional. |
| RES-005 | Los requisitos están respaldados por fuentes verificables. |
| RES-006 | La plataforma indica su carácter de prototipo independiente. |
| RES-007 | Los datos personales se minimizan. |
| RES-008 | El MVP es desplegable y demostrable. |
| RES-009 | Las operaciones administrativas del catálogo están protegidas. |
| RES-010 | El alcance inicial no incluye reconocimiento institucional de documentos generados. |

# 13. Supuestos y dependencias

| ID | Tipo | Descripción |
|---|---|---|
| SUP-001 | Supuesto | Existe documentación pública suficiente para un conjunto inicial de trámites. |
| SUP-002 | Supuesto | Los documentos pueden organizarse en un catálogo estructurado. |
| SUP-003 | Supuesto | Los usuarios describen sus necesidades en lenguaje natural. |
| SUP-004 | Supuesto | Se puede construir un conjunto de casos de prueba representativo. |
| SUP-005 | Supuesto | Las fuentes oficiales permiten identificar parte de los requisitos. |
| SUP-006 | Supuesto | La solución opera inicialmente sin integración institucional. |
| DEP-001 | Dependencia | Disponibilidad de documentos institucionales. |
| DEP-002 | Dependencia | Calidad y vigencia de las fuentes. |
| DEP-003 | Dependencia | Identificación de unidades responsables. |
| DEP-004 | Dependencia | Disponibilidad de un modelo de lenguaje. |
| DEP-005 | Dependencia | Herramientas de recuperación documental. |
| DEP-006 | Dependencia | Entorno de despliegue. |
| DEP-007 | Dependencia | Validación de casos y respuestas esperadas. |
| DEP-008 | Dependencia | Participación de usuarios para pruebas de utilidad. |

# 14. Riesgos

| ID | Riesgo | Impacto | Mitigación |
|---|---|---|---|
| RSK-001 | Información institucional desactualizada. | Alto | Control de vigencia y revisión periódica. |
| RSK-002 | Requisitos diferentes según carrera o condición. | Alto | Condiciones explícitas por trámite en el catálogo. |
| RSK-003 | Respuestas incorrectas del agente. | Alto | Fuentes verificables, reglas y evaluación. |
| RSK-004 | Interpretación de la herramienta como canal oficial. | Alto | Avisos explícitos de naturaleza independiente. |
| RSK-005 | Documentación incompleta. | Alto | Abstención y derivación a canales oficiales. |
| RSK-006 | Cambios normativos. | Alto | Versionado y revisión del conocimiento. |
| RSK-007 | Exposición de datos personales. | Alto | Minimización y controles de seguridad. |
| RSK-008 | Falta de participación institucional. | Medio | MVP independiente con información pública. |
| RSK-009 | Complejidad excesiva del catálogo. | Alto | Selección acotada de trámites. |
| RSK-010 | Costos de inferencia. | Medio | Límites de uso y monitoreo. |
| RSK-011 | Contradicciones entre documentos. | Alto | Detección y revisión humana. |
| RSK-012 | Enlaces oficiales inaccesibles. | Medio | Verificación periódica y referencia documental. |
| RSK-013 | Confusión entre orientación y validación oficial. | Alto | Diferenciación explícita de responsabilidades. |
| RSK-014 | Falta de evidencia para medir beneficios. | Medio | Pruebas controladas y métricas verificables. |

# 15. Entregables del MVP

## 15.1 Lista de entregables

**Objetivo:** demostrar orientación verificable sobre los dos trámites definidos.

| # | Entregable | Estado |
|---|---|---|
| 1 | Catálogo de trámites | ✅ Dos trámites |
| 2 | Repositorio de documentación oficial | ◐ Enlaces a las fuentes; no se almacenan copias |
| 3 | Identificación de fuentes y vigencia | ✅ Fuente, fecha, estado de vigencia e historial del catálogo |
| 4 | Agente conversacional | ✅ `asistente.py` |
| 5 | Recuperación de información documental | ○ RAG disponible como práctica, no conectado |
| 6 | Identificación contextual de procedimientos | ◐ Dos trámites; la identificación la hace el modelo |
| 7 | Motor de requisitos condicionados | ✅ Nacionalidad, carrera y excelencia académica |
| 8 | Listas de verificación | ✅ `revisar_requisitos`: cumplidos, pendientes y desconocidos |
| 9 | Explicación de dependencias | ✅ `consultar_dependencias`: Diploma Académico → Título Profesional |
| 10 | Respuestas con referencias | ✅ Enlace oficial y fecha de revisión |
| 11 | Casos de prueba | ✅ 53 pruebas offline, con banco de consultas de referencia |
| 12 | Despliegue funcional | ◐ Código listo; falta repositorio Git y Render |

Leyenda: ✅ implementado · ◐ parcial · ○ pendiente.

## 15.2 Estado de implementación del MVP

**Corte:** 31 de octubre de 2026.

| Trámite | Unidad | Fuente | Revisión |
|---|---|---|---|
| Obtención del Diploma Académico | División de Títulos y Diplomas | [Instructivo oficial](https://titulos.umsa.bo/web/guest/80/-/asset_publisher/EqYqDCs5RT2H/content/requisitos-para-diploma-academico-gestion-2019/20142) | 31/10/2026 |
| Título Profesional (ex Provisión Nacional), R-271 v10 | División de Títulos y Diplomas | [Instructivo oficial](https://titulos.umsa.bo/web/guest/80/-/asset_publisher/EqYqDCs5RT2H/content/requisitos-para-titulo-profesional-gestion-2019/20142) | 31/10/2026 |

**Componentes.** Capability `tramites` con las tools `listar_tramites`, `consultar_tramite`, `revisar_requisitos`, `consultar_dependencias` y `estado_catalogo`; catálogo `TRAMITES` con las fichas verificadas, una clave por requisito, estado de vigencia e historial; dependencias documentadas en `DEPENDENCIAS`; agente con instrucciones de TRAMIA; canal Telegram con lista de permitidos.

**Requisitos cubiertos.** RN-002 (solo datos del catálogo), RN-004 (datos faltantes en `por_confirmar`), RN-005 (una ficha sin revisar hace más de 180 días deja de presentarse como vigente), RN-009 (lo declarado no se presenta como verificado), RN-006 y RN-018 (aviso de prototipo), BR-005 (vigencia, por verificar y desactualizado), BR-012/013/016 (requisitos y condiciones), BR-014/015 (lista de verificación y detección de faltantes), BR-017/018 (dependencias y orden), BR-021/022 (fuente y fecha) y BR-025 (historial de cambios del catálogo).

**Limitaciones.** Sin memoria conversacional (cada mensaje empieza de cero, así que la lista de verificación se arma por mensaje); la coincidencia de documentos es por claves del catálogo, así que una forma muy distinta de nombrar un documento aparece en `no_reconocidos` y se pregunta; la revisión de vigencia es manual y el historial registra los cambios del **catálogo**, no las versiones oficiales de los instructivos (la versión oficial solo se conoce cuando la fuente la publica, como R-271 v10); el plazo del Título Profesional (20/11/2026) y los costos deben revisarse cada periodo; el MVP cubre solo el Diploma Académico y el Título Profesional; sin integración institucional ni emisión de documentos; no almacena datos personales.

**Operación.** Fuentes: instructivos públicos de titulos.umsa.bo. El catálogo se revisa al inicio de cada gestión académica y antes de cada periodo de recepción de trámites; no debe presentarse como vigente pasados 6 meses sin revisión. La actualización es manual, una vez por gestión. El MVP no almacena datos personales, no requiere responsables de validación ni colaboración institucional.

**Verificación.** `uv run pytest` ejecuta 53 pruebas sin modelo real, incluido el banco de consultas de referencia de `tests/test_referencia.py` y los casos de lista de verificación.

# 16. Criterios de aceptación

| ID | Criterio |
|---|---|
| AC-001 | El usuario consulta trámites en lenguaje natural. |
| AC-002 | El sistema identifica el trámite a partir de una necesidad cotidiana. |
| AC-003 | El agente pide información adicional cuando la carrera o situación afecta los requisitos. |
| AC-004 | Los requisitos presentados están respaldados por fuentes oficiales. |
| AC-005 | El agente genera una lista de verificación adaptada a las condiciones conocidas. |
| AC-006 | La lista diferencia requisitos cumplidos, pendientes y desconocidos. |
| AC-007 | El sistema explica dependencias documentadas entre trámites. |
| AC-008 | El agente proporciona enlaces o referencias verificables. |
| AC-009 | Costos y plazos no se inventan cuando no están disponibles. |
| AC-010 | El sistema detecta información contradictoria y evita presentarla como definitiva. |
| AC-011 | El agente reconoce consultas fuera del alcance del catálogo. |
| AC-012 | El sistema informa que no sustituye a las unidades oficiales. |
| AC-013 | Los cambios administrativos del catálogo requieren autorización. |
| AC-014 | No se consultan ni modifican expedientes privados sin integración autorizada. |
| AC-015 | Las respuestas pueden evaluarse contra casos de referencia. |
| AC-016 | El prototipo está desplegado y disponible para demostración. |

# 17. Matriz de trazabilidad

| Objetivo | Requerimientos | Indicadores |
|---|---|---|
| OBJ-001 | BR-001 a BR-020 | KPI-001, KPI-002, KPI-007 |
| OBJ-002 | BR-001 a BR-005 | KPI-003 |
| OBJ-003 | BR-006 a BR-011 | KPI-001 |
| OBJ-004 | BR-012, BR-013, BR-016 | KPI-002, KPI-005 |
| OBJ-005 | BR-014, BR-015 | KPI-010 |
| OBJ-006 | BR-017, BR-018 | KPI-010 |
| OBJ-007 | BR-021, BR-022, BR-025 | KPI-004 |
| OBJ-008 | BR-005, BR-023, BR-026 | KPI-006, KPI-009 |
| OBJ-009 | BR-019, BR-020 | KPI-011 |
| OBJ-010 | BR-006, BR-014 | KPI-007, KPI-008 |
| OBJ-011 | BR-031, BR-034 a BR-036 | No aplica en el MVP |
| OBJ-012 | BR-032, BR-033 | KPI-001 a KPI-012 |

La cadena completa es **BRD → PRD → SDD → HU → Casos de prueba**.

# 18. Consideraciones de diseño

Los procedimientos no deben quedar codificados en las instrucciones del modelo. El conocimiento se organiza como catálogo: requisitos, condiciones, documentos, versiones, relaciones entre trámites, unidades y canales. La inteligencia artificial interpreta consultas y redacta respuestas, pero no sustituye las validaciones deterministas.

# 19. Conclusiones

TRAMIA propone mejorar la orientación sobre procedimientos universitarios mediante conocimiento institucional estructurado y respuestas verificables. Su valor está en identificar el procedimiento adecuado, comprender condiciones particulares, organizar requisitos, explicar dependencias y derivar a los canales oficiales.

El proyecto se limita a dos trámites con documentación oficial verificada. Cualquier integración con sistemas universitarios requerirá autorización institucional y mecanismos de autenticación y protección de información.

## 19.1 Enlaces de referencia

- Trámites — División de Títulos y Diplomas: <https://titulos.umsa.bo/tramites>

## 19.2 Historial de cambios

| Versión | Fecha | Cambio |
|---|---|---|
| 1.0 | 31/10/2026 | BRD inicial. |
| 1.1 | 31/10/2026 | Estado del MVP, entregables y validaciones. |
| 1.2 | 31/10/2026 | Documento reducido; se conservan todos los identificadores y el estado del MVP. |
| 1.3 | 31/10/2026 | Alcance alineado a titulos.umsa.bo/tramites; se eliminan referencias a otras unidades. |
| 1.4 | 31/10/2026 | Se unifica el alcance en un solo MVP de dos trámites; se elimina la ampliación prevista. |
| 1.5 | 31/10/2026 | Nombre definitivo: TRAMIA, enfocado en la UMSA; se retira esa validación pendiente. |
| 1.6 | 31/10/2026 | Se cierran las validaciones pendientes: fuentes, revisión por gestión, operación y banco de pruebas de referencia. |
| 1.7 | 31/10/2026 | Lista de verificación: tool `revisar_requisitos` y claves por requisito (BR-014/015, AC-005/006). |
| 1.8 | 31/10/2026 | Dependencias documentadas (`consultar_dependencias`) y vigencia con historial (`estado_catalogo`): BR-017/018 y BR-005/025. |

---

**Fin del documento BRD — Versión 1.8**
