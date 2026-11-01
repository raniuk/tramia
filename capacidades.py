"""Las capabilities de TRAMIA y las de práctica del curso: cámbialas o agrega las tuyas.

Una Capability junta tools + instrucciones en una pieza que se enchufa al agente (asistente.py).
El docstring y los tipos de cada tool son lo único que el modelo lee para decidir cuándo usarla.
"""

import csv
import sqlite3
import unicodedata
from datetime import date
from functools import cache
from typing import Literal

import chromadb
import httpx
from langchain_text_splitters import RecursiveCharacterTextSplitter
from openai import OpenAI
from pydantic_ai.capabilities import Capability
from pypdf import PdfReader

from config import DATOS, settings

# ═══ S1 · Tools de lectura con APIs públicas ══════════════════════════════════════════
apis = Capability(
    id="apis_publicas",
    description="Consulta indicadores económicos (Banco Mundial) y clima (Open Meteo) con sus APIs públicas",
    instructions="Usa las APIs para obtener datos reales. Si una API no tiene el dato, dilo, y no inventes datos",
)


@apis.tool_plain
def inflacion(pais: str, anio: int) -> dict:
    """Inflación anual de un país en un año, según el Banco Mundial.

    Args:
        pais: código ISO del país, por ejemplo 'BO' para Bolivia o 'PE' para Perú
        anio: año, por ejemplo 2024
    """
    url = f"https://api.worldbank.org/v2/country/{pais}/indicator/FP.CPI.TOTL.ZG"
    respuesta = httpx.get(url, params={"date": anio, "format": "json"}, timeout=10)
    respuesta.raise_for_status()
    datos = respuesta.json()

    # La API responde [metadatos, registros]. Si no hay dato, devolvemos un aviso que el modelo puede leer
    if len(datos) < 2 or not datos[1] or datos[1][0]["value"] is None:
        return {"error": f"No hay datos de inflación disponibles para {pais} en {anio}"}

    registro = datos[1][0]
    return {
        "pais": registro["country"]["value"],
        "anio": registro["date"],
        "inflacion_pct": round(registro["value"], 2),
        "fuente": "Banco Mundial",  # devolver la fuente evita que el modelo invente una
    }


@apis.tool_plain
def clima_cochabamba() -> dict:
    """Temperatura actual de Cochabamba, según Open Meteo."""
    params = {"latitude": -17.38, "longitude": -66.15, "current": "temperature_2m"}
    respuesta = httpx.get("https://api.open-meteo.com/v1/forecast", params=params, timeout=10)
    respuesta.raise_for_status()
    return {"temperatura": respuesta.json()["current"]["temperature_2m"], "fuente": "Open Meteo"}


# ═══ S1 · Mi contador: gastos en SQLite, una tool que lee y otra que escribe ══════════
Categoria = Literal["transporte", "alimentacion", "educacion", "ocio", "salud"]
CSV = DATOS / "gastos.csv"  # 10 gastos ficticios de mayo de 2030
DB = DATOS / "gastos.db"  # la base: se crea desde el CSV la primera vez


def crear_base() -> None:
    """Crea gastos.db desde cero con los gastos del CSV."""
    DB.unlink(missing_ok=True)
    with CSV.open(encoding="utf-8") as archivo:
        filas = [(g["fecha"], g["categoria"], g["descripcion"], float(g["monto"])) for g in csv.DictReader(archivo)]
    conexion = sqlite3.connect(DB)
    with conexion:
        conexion.execute(
            "CREATE TABLE gastos (fecha TEXT, categoria TEXT, descripcion TEXT, monto REAL CHECK (monto > 0))"
        )
        conexion.executemany("INSERT INTO gastos VALUES (?, ?, ?, ?)", filas)
    conexion.close()


def hoy() -> str:
    """Instrucción dinámica: el modelo no sabe qué día es; se lo decimos en cada mensaje."""
    return f"Hoy es {date.today().isoformat()}."


# Lectura y escritura van en capabilities separadas: a otro agente le podrías dar solo la primera
consulta = Capability(
    id="consulta_gastos",
    description="Consulta gastos personales almacenados en una base de datos SQLite",
    instructions="Usa la base de datos para responder preguntas sobre los gastos. No inventes datos.",
)
registro = Capability(
    id="registro_gastos",
    description="Registra nuevos gastos en la base de datos SQLite",
    instructions=["Agrega nuevos gastos a la base de datos. Asegúrate de que los datos sean válidos.", hoy],
)


@consulta.tool_plain
def consultar_gastos(categoria: Categoria) -> dict:
    """Gastos de una categoría y su total en bolivianos."""
    if not DB.exists():
        crear_base()
    conexion = sqlite3.connect(DB.resolve().as_uri() + "?mode=ro", uri=True)  # solo lectura
    conexion.row_factory = sqlite3.Row  # cada fila como diccionario
    filas = conexion.execute(
        "SELECT fecha, descripcion, monto FROM gastos WHERE categoria = ?",  # SQL fijo; el valor va en ?
        (categoria,),
    ).fetchall()
    conexion.close()
    return {"categoria": categoria, "total_bs": sum(f["monto"] for f in filas), "gastos": [dict(f) for f in filas]}


@registro.tool_plain
def registrar_gasto(fecha: str, categoria: Categoria, descripcion: str, monto: float) -> str:
    """Anota un gasto nuevo. La fecha va como AAAA-MM-DD y el monto en bolivianos."""
    if not DB.exists():
        crear_base()
    conexion = sqlite3.connect(DB)  # sin mode=ro: esta tool sí escribe
    try:
        with conexion:  # transacción: guarda todo o nada
            conexion.execute("INSERT INTO gastos VALUES (?, ?, ?, ?)", (fecha, categoria, descripcion, monto))
    except sqlite3.IntegrityError:  # el CHECK de la tabla rechaza montos de 0 o negativos
        return f"No se guardó: el monto debe ser mayor que 0 (recibí {monto})."
    finally:
        conexion.close()
    return f"Gasto registrado: {descripcion}, {monto} Bs en {categoria} el {fecha}."


# ═══ S2 · RAG: buscar en mis documentos (PDFs) y citar la fuente ══════════════════════
DOCUMENTOS = DATOS / "documentos"  # PDFs ficticios de finanzas personales


def embeddings_de(textos: list[str]) -> list[list[float]]:
    """Convierte cada texto en un vector: textos de significado parecido dan vectores cercanos."""
    # Gemini también ofrece una API compatible con la de OpenAI; la usamos para los embeddings
    cliente = OpenAI(
        api_key=settings.gemini_api_key_local.get_secret_value(),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    )
    respuesta = cliente.embeddings.create(model="gemini-embedding-001", input=textos)
    return [item.embedding for item in respuesta.data]


@cache  # se indexa la primera vez que alguien busca, y una sola vez mientras el programa corre
def indice():
    # Base vectorial en memoria (se pierde al terminar); "cosine" mide la cercanía por el ángulo
    coleccion = chromadb.EphemeralClient().get_or_create_collection(
        "documentos", configuration={"hnsw": {"space": "cosine"}}
    )
    for pdf in sorted(DOCUMENTOS.glob("*.pdf")):
        texto = "\n".join(pagina.extract_text() for pagina in PdfReader(pdf).pages)
        # Trozos de ~300 caracteres que se solapan 50, para no cortar una idea por la mitad
        trozos = RecursiveCharacterTextSplitter(chunk_size=300, chunk_overlap=50).split_text(texto)
        coleccion.upsert(
            ids=[f"{pdf.stem}-{i}" for i in range(len(trozos))],  # el id dice de qué PDF sale: sirve para citar
            documents=trozos,
            embeddings=embeddings_de(trozos),
        )
    return coleccion


def buscar(pregunta: str, k: int = 3) -> list[dict]:
    """Los k trozos más parecidos a la pregunta, con su fuente y su similitud (1 = idéntico)."""
    r = indice().query(query_embeddings=embeddings_de([pregunta]), n_results=k)
    return [
        {"fuente": fuente, "similitud": round(1 - distancia, 2), "texto": texto}
        for fuente, distancia, texto in zip(r["ids"][0], r["distances"][0], r["documents"][0])
    ]


documentos = Capability(
    id="mis_documentos",
    description="Documentos de finanzas personales: contratos, facturas y garantías",
    # Citar la fuente y admitir cuando no hay datos: así se ve qué sale de los documentos y qué no
    instructions=(
        "Para preguntas sobre pagos, contratos o garantías usa buscar_documentos y cita la fuente "
        "entre corchetes, por ejemplo [contrato_alquiler-1]. "
        "Si no hay información suficiente para responder, di que no lo encuentras, no lo inventes."
    ),
)


@documentos.tool_plain
def buscar_documentos(pregunta: str) -> list[dict]:
    """Busca en los documentos los fragmentos que responden a la pregunta."""
    resultados = buscar(pregunta, k=3)
    for r in resultados:  # en la terminal (o en los Logs de Render) se ve qué recuperó
        print(f"  📄 {r['fuente']} (similitud {r['similitud']})", flush=True)
    return resultados


# ═══ TRAMIA · Trámites de la UMSA: requisitos, costos y pasos con su fuente ══════════
# Datos de la División de Títulos y Diplomas, gestión 2026, revisados el 31/10/2026.
REVISADO = "2026-10-31"  # última revisión de cada ficha contra su instructivo
VIGENCIA_DIAS = 180  # el BRD: pasados 6 meses sin revisión, no se presenta como vigente

Tramite = Literal["diploma_academico", "titulo_profesional"]
Nacionalidad = Literal["boliviana", "extranjera"]
Carrera = Literal["medicina", "odontologia", "enfermeria", "informatica", "derecho", "otra"]

TRAMITES = {
    "diploma_academico": {
        "nombre": "Obtención del Diploma Académico (gestión 2026)",
        "codigo": None,  # la página no publica código ni versión de este instructivo
        "fuente": "https://titulos.umsa.bo/web/guest/80/-/asset_publisher/EqYqDCs5RT2H/content/requisitos-para-diploma-academico-gestion-2019/20142",
        "revisado": REVISADO,
        "estado": "vigente",  # marca humana (BR-026): pasa a "desactualizado" si se publica un instructivo nuevo
        "historial": [{"fecha": REVISADO, "cambio": "Carga inicial del instructivo publicado para la gestión 2026"}],
        "costos": [
            {"concepto": "Técnico Universitario Superior o Medio", "monto_bs": 686},
            {"concepto": "Nacionales, Licenciatura", "monto_bs": 1343},
            {"concepto": "Extranjeros, Licenciatura", "monto_bs": 2661},
        ],
        "inicio": [
            "Trámite digital: iniciar y elegir el pago electrónico en tramitesenlinea.umsa.bo",
            "Trámite físico: acudir a la División de Títulos y Diplomas (Edificio Melissa) para el pago en caja y el formulario manuscrito",
        ],
        "requisitos": [
            {
                "descripcion": "Certificado de Calificaciones de Grado original, con firmas y sellos verificados",
                "claves": ["calificaciones", "notas de grado"],
            },
            {
                "descripcion": "Fotocopia legalizada del Acta de Modalidad de Graduación, con el recibo original",
                "claves": ["acta", "modalidad de graduacion"],
            },
            {
                "descripcion": "Certificado actualizado de la Biblioteca Central que acredite no deber libros",
                "claves": ["biblioteca"],
            },
            {
                "descripcion": "Certificado de entrega de Tesis, Trabajo Dirigido o Proyecto, con CDs y resumen",
                "claves": ["tesis", "trabajo dirigido", "proyecto de grado"],
            },
            {
                "descripcion": "Certificado actualizado de la encuesta del DSIE (sia.umsa.bo/encuesta)",
                "claves": ["dsie", "encuesta"],
            },
            {
                "descripcion": "Certificado de no adeudo económico emitido por el Departamento de Contabilidad",
                "claves": ["contabilidad", "adeudo"],
            },
            {
                "descripcion": "Fotocopia de la matrícula de la última gestión y de la Cédula de Identidad",
                "claves": ["matricula", "cedula", "carnet"],
            },
            {
                "descripcion": "Certificado de Nacimiento original computarizado y fotocopia del Diploma de Bachiller",
                "claves": ["nacimiento", "bachiller"],
            },
            {
                "descripcion": "Dos fotografías de 3,5 x 3,5 cm, fondo plomo claro, papel mate, no digitales",
                "claves": ["fotografia", "fotos"],
            },
        ],
        "entrega": ["Toda la documentación va en un sobre plástico con broches, sin perforar"],
        "notas": [
            "El Diploma Académico se otorga una sola vez; si se pierde o deteriora, se tramita un Certificado Supletorio",
        ],
    },
    "titulo_profesional": {
        "nombre": "Título Profesional (ex Provisión Nacional), gestión 2026",
        "codigo": "R-271, versión 10, aprobado el 12/06/2026",
        "fuente": "https://titulos.umsa.bo/web/guest/80/-/asset_publisher/EqYqDCs5RT2H/content/requisitos-para-titulo-profesional-gestion-2019/20142",
        "revisado": REVISADO,
        "estado": "vigente",  # marca humana (BR-026): pasa a "desactualizado" si se publica un instructivo nuevo
        "historial": [{"fecha": REVISADO, "cambio": "Carga inicial del R-271 v10, aprobado el 12/06/2026"}],
        "costos": [
            {"concepto": "Nacionales, Licenciatura", "monto_bs": 2242},
            {"concepto": "Extranjeros, Licenciatura", "monto_bs": 4846},
            {"concepto": "Técnico Universitario Superior", "monto_bs": 1229},
            {"concepto": "Técnico Universitario Medio", "monto_bs": 1229},
            {"concepto": "Excelencia Académica", "monto_bs": 0, "detalle": "Liberado; exige la liberación formal en la Caja Recaudadora"},
        ],
        "inicio": [
            "Pagar en línea e imprimir el formulario de solicitud en tamaño oficio desde tramitesenlinea.umsa.bo",
            "Escanear y subir los documentos obligatoriamente en titula.umsa.bo",
            "Alternativa: pagar en la Caja del Edificio Melissa si ya se tiene toda la documentación física",
        ],
        "requisitos": [
            {
                "descripcion": "Fotocopia del Diploma Académico legalizada por la UMSA (Legalizaciones, División de Archivo, Monoblock Central, 2.º patio)",
                "claves": ["diploma", "legalizacion del diploma", "diploma legalizado"],
            },
            {
                "descripcion": "Certificado de Nacimiento original actualizado al año de presentación",
                "claves": ["nacimiento"],
            },
            {
                "descripcion": "Una fotografía a color de 3,5 x 3,5 cm, fondo plomo claro, sin bordes; no se aceptan digitales",
                "claves": ["fotografia", "fotos"],
            },
            {
                "descripcion": "Fotocopia simple de la Cédula de Identidad vigente",
                "claves": ["cedula", "carnet"],
            },
            {
                "descripcion": "Sobre blanco pequeño rotulado con apellido paterno, materno, nombres, teléfono y correo",
                "claves": ["sobre"],
            },
            {
                "descripcion": "Certificado de Nacimiento legalizado por consulado boliviano y Cancillería, o apostillado; traducción en CETI si está en otro idioma",
                "cuando": {"nacionalidad": ["extranjera"]},
                "claves": ["nacimiento legalizado", "apostillado", "consulado", "ceti"],
            },
            {
                "descripcion": "Fotocopia legalizada de la Resolución Administrativa del Servicio Social de Salud Rural Obligatorio (D.L. 15629 y D.S. 26217)",
                "cuando": {"carrera": ["medicina", "odontologia", "enfermeria"]},
                "claves": ["servicio social", "salud rural", "rural obligatorio"],
            },
            {
                "descripcion": "Informe original de Decanato con la mención correspondiente y pago de Bs 15 por la mención",
                "cuando": {"carrera": ["informatica"]},
                "claves": ["mencion", "decanato"],
            },
            {
                "descripcion": "Exámenes de igualación en materias afines a la legislación nacional o desempeño como Asesor Legal en un consultorio jurídico de la Facultad (Res. Fac. 62/95)",
                "cuando": {"carrera": ["derecho"]},
                "claves": ["igualacion", "asesor legal", "consultorio juridico"],
            },
            {
                "descripcion": "Certificado de Calificaciones de Grado original y fotocopia simple del Record Académico (D.S. 1322 y Res. H.C.U. 421/2013)",
                "cuando": {"excelencia_academica": [True]},
                "claves": ["record academico", "calificaciones de grado"],
            },
        ],
        "entrega": [
            "Interesado: Cédula de Identidad y copia del recibo de pago",
            "Padre o madre: fotocopia de C.I., fotocopia del Certificado de Nacimiento del hijo y copia del recibo",
            "Terceras personas: Poder Notarial original y copia del recibo de pago",
        ],
        "notas": [
            "Recepción de trámites hasta el 20 de noviembre de 2026",
            "Presentar los documentos en fólder color marfil, sueltos, sin engrapar ni perforar",
            "El trámite concluye pasados 30 días calendario y se recoge en la misma oficina donde se inició",
            "Se otorga una sola vez; en caso de extravío o deterioro se tramita un Certificado Supletorio",
            "Los requisitos anteriores para Título Profesional quedan nulos",
        ],
    },
}

# Dependencias documentadas entre trámites del catálogo (BR-017 y BR-018).
# Solo va una dependencia si el instructivo la dice: aquí, el Título Profesional exige el Diploma Académico.
DEPENDENCIAS = {
    "titulo_profesional": [
        {
            "tramite": "diploma_academico",
            "motivo": "El instructivo del Título Profesional exige la fotocopia legalizada del Diploma Académico",
            "paso_previo": "Legalizar el Diploma Académico en Legalizaciones, División de Archivo (Monoblock Central, 2.º patio)",
        },
    ],
}


def aplica(cuando: dict, datos: dict) -> bool | None:
    """True si se cumplen las condiciones, False si no, None si falta el dato (hay que preguntarlo)."""
    for campo, valores in cuando.items():
        valor = datos.get(campo)
        if valor is None:
            return None
        if valor not in valores:
            return False
    return True


def normalizar(texto: str) -> str:
    """Minúsculas y sin tildes: 'Cédula' y 'cedula' se comparan igual."""
    sin_tildes = unicodedata.normalize("NFD", texto.lower())
    return " ".join("".join(c for c in sin_tildes if not unicodedata.combining(c)).split())


NEGACIONES = ("no tengo", "no lo tengo", "no la tengo", "me falta", "me faltan", "todavia no", "aun no")


def es_negacion(declarado: str) -> bool:
    """'no tengo el diploma' declara una ausencia: no se cuenta como documento presentado."""
    texto = normalizar(declarado)
    return any(negacion in texto for negacion in NEGACIONES)


def coincide(declarado: str, requisito: dict) -> bool:
    """True si lo que el usuario dice tener se reconoce en una clave del requisito o en su descripción.

    Es deliberadamente estricto: si no coincide, el requisito queda pendiente o como no reconocido,
    nunca como cumplido por parecido. Es el equivalente a RN-009: lo declarado no está verificado.
    """
    texto = normalizar(declarado)
    if texto in normalizar(requisito["descripcion"]):
        return True
    return any(clave in texto for clave in map(normalizar, requisito.get("claves", ())))


def requisitos_aplicables(ficha: dict, datos: dict) -> tuple[list[dict], list[dict], list[dict], set[str]]:
    """Reparte los requisitos del trámite en: obligatorios, condicionales que aplican,
    condicionales que no se pueden decidir todavía y los datos que hay que preguntar."""
    obligatorios, condicionales, desconocidos, por_confirmar = [], [], [], set()
    for requisito in ficha["requisitos"]:
        cuando = requisito.get("cuando")
        if not cuando:
            obligatorios.append(requisito)
            continue
        resultado = aplica(cuando, datos)
        if resultado is None:  # falta un dato: el modelo debe preguntarlo, no suponerlo
            desconocidos.append(requisito)
            por_confirmar.update(campo for campo in cuando if datos.get(campo) is None)
        elif resultado:
            condicionales.append(requisito)
    return obligatorios, condicionales, desconocidos, por_confirmar


def vigencia(ficha: dict, dia: date | None = None) -> dict:
    """Estado de vigencia de una ficha: vigente, por verificar o desactualizada (BR-005 y RN-005).

    Pasados VIGENCIA_DIAS sin revisión deja de ser 'vigente' a propósito: el BRD no permite
    presentar el catálogo como actual si nadie lo revisó. El estado 'desactualizado' es la marca
    humana que se pone cuando aparece un instructivo nuevo (BR-026).
    """
    hoy = dia or date.today()
    dias = (hoy - date.fromisoformat(ficha["revisado"])).days
    if ficha.get("estado") == "desactualizado":
        estado = "desactualizado"
        aviso = "La ficha está marcada como desactualizada: confirma en el canal oficial antes de usarla."
    elif dias > VIGENCIA_DIAS:
        estado = "por_verificar"
        aviso = f"Sin revisión desde el {ficha['revisado']} ({dias} días): confirma en el canal oficial antes de presentar documentos."
    else:
        estado = "vigente"
        aviso = f"Catálogo revisado el {ficha['revisado']} (hace {dias} días)."
    return {"estado": estado, "revisado": ficha["revisado"], "dias_sin_revisar": dias, "aviso": aviso}


tramites = Capability(
    id="tramites_umsa",
    description="Requisitos, costos y pasos de trámites de la División de Títulos y Diplomas de la UMSA",
    instructions=[
        "Responde sobre trámites solo con lo que devuelvan estas tools. No inventes requisitos, costos ni plazos.",
        "Si la respuesta trae 'por_confirmar', pregunta esos datos antes de dar requisitos condicionales.",
        "Si el usuario dice qué documentos ya tiene, usa revisar_requisitos y dile qué le falta; "
        "no afirmes que ya cumplió un requisito si la tool no lo puso en 'cumplidos'.",
        "Lo que el usuario dice tener no está verificado por la UMSA: preséntalo como declarado, no como aprobado.",
        "Si preguntan qué hacer primero, si un trámite depende de otro o si pueden saltarse un paso, usa consultar_dependencias.",
        "Si preguntan si la información está actualizada, usa estado_catalogo.",
        "Si 'vigencia.estado' no es 'vigente', dilo antes de dar requisitos y recomienda confirmar en el canal oficial.",
        "Cita la fuente y aclara que es orientación de un prototipo independiente, no una confirmación oficial de la UMSA.",
        hoy,  # el modelo no sabe qué día es: sirve para razonar sobre el plazo de recepción
    ],
)


@tramites.tool_plain
def listar_tramites() -> list[dict]:
    """Trámites disponibles en el catálogo, con su identificador y su fuente oficial."""
    return [{"id": clave, "nombre": ficha["nombre"], "fuente": ficha["fuente"]} for clave, ficha in TRAMITES.items()]


@tramites.tool_plain
def consultar_tramite(
    tramite: Tramite,
    nacionalidad: Nacionalidad | None = None,
    carrera: Carrera | None = None,
    excelencia_academica: bool | None = None,
) -> dict:
    """Requisitos, costos, pasos y fuente oficial de un trámite de la UMSA.

    Args:
        tramite: identificador del trámite, según listar_tramites
        nacionalidad: boliviana o extranjera, solo si el usuario lo dijo
        carrera: carrera del solicitante, solo si cambia los requisitos
        excelencia_academica: True si se graduó con excelencia académica
    """
    ficha = TRAMITES.get(tramite)
    if ficha is None:
        return {"error": f"No tengo el trámite {tramite} en el catálogo"}

    datos = {"nacionalidad": nacionalidad, "carrera": carrera, "excelencia_academica": excelencia_academica}
    obligatorios, condicionales, _, por_confirmar = requisitos_aplicables(ficha, datos)

    return {
        "tramite": ficha["nombre"],
        "unidad": "División de Títulos y Diplomas - UMSA",
        "gestion": "2026",
        "codigo": ficha["codigo"],
        "fuente": ficha["fuente"],
        "vigencia": vigencia(ficha),
        "requiere_antes": [previo["tramite"] for previo in DEPENDENCIAS.get(tramite, [])],
        "requisitos_obligatorios": [r["descripcion"] for r in obligatorios],
        "requisitos_condicionales": [r["descripcion"] for r in condicionales],
        "por_confirmar": sorted(por_confirmar),
        "costos_bs": ficha["costos"],
        "inicio": ficha["inicio"],
        "entrega": ficha["entrega"],
        "notas": ficha["notas"],
    }


@tramites.tool_plain
def revisar_requisitos(
    tramite: Tramite,
    tengo: list[str],
    nacionalidad: Nacionalidad | None = None,
    carrera: Carrera | None = None,
    excelencia_academica: bool | None = None,
) -> dict:
    """Lista de verificación: compara los documentos que el usuario ya tiene con los requisitos del trámite.

    Args:
        tramite: identificador del trámite, según listar_tramites
        tengo: documentos que el usuario dice tener, en sus palabras ("certificado de biblioteca", "fotos")
        nacionalidad: boliviana o extranjera, solo si el usuario lo dijo
        carrera: carrera del solicitante, solo si cambia los requisitos
        excelencia_academica: True si se graduó con excelencia académica
    """
    ficha = TRAMITES.get(tramite)
    if ficha is None:
        return {"error": f"No tengo el trámite {tramite} en el catálogo"}

    datos = {"nacionalidad": nacionalidad, "carrera": carrera, "excelencia_academica": excelencia_academica}
    obligatorios, condicionales, desconocidos, por_confirmar = requisitos_aplicables(ficha, datos)

    declarados = [documento.strip() for documento in tengo if documento.strip() and not es_negacion(documento)]
    conocidos = obligatorios + condicionales
    cumplidos = [r["descripcion"] for r in conocidos if any(coincide(d, r) for d in declarados)]
    pendientes = [r["descripcion"] for r in conocidos if not any(coincide(d, r) for d in declarados)]
    # Lo declarado que no coincide con ningún requisito se devuelve tal cual: el modelo lo pregunta,
    # en vez de darlo por bueno (RN-002 y RN-009)
    no_reconocidos = [
        documento for documento in declarados if not any(coincide(documento, r) for r in conocidos + desconocidos)
    ]

    return {
        "tramite": ficha["nombre"],
        "fuente": ficha["fuente"],
        "vigencia": vigencia(ficha),
        "cumplidos": cumplidos,
        "pendientes": pendientes,
        "por_confirmar": sorted(por_confirmar),
        "desconocidos": [r["descripcion"] for r in desconocidos],
        "no_reconocidos": no_reconocidos,
        "aviso": "Lo que el usuario declara no está verificado por la UMSA: la lista orienta, no valida el expediente.",
    }


@tramites.tool_plain
def consultar_dependencias(tramite: Tramite) -> dict:
    """Dependencias documentadas de un trámite: qué hay que hacer antes y en qué orden.

    Args:
        tramite: identificador del trámite, según listar_tramites
    """
    ficha = TRAMITES.get(tramite)
    if ficha is None:
        return {"error": f"No tengo el trámite {tramite} en el catálogo"}

    previos = DEPENDENCIAS.get(tramite, [])
    return {
        "tramite": ficha["nombre"],
        "requiere_antes": [
            {
                "tramite": previo["tramite"],
                "nombre": TRAMITES[previo["tramite"]]["nombre"],
                "motivo": previo["motivo"],
                "paso_previo": previo["paso_previo"],
                "fuente": TRAMITES[previo["tramite"]]["fuente"],
            }
            for previo in previos
        ],
        "orden": [previo["tramite"] for previo in previos] + [tramite],
        "vigencia": vigencia(ficha),
        "aviso": "Solo se explican dependencias documentadas en los instructivos del catálogo.",
    }


@tramites.tool_plain
def estado_catalogo() -> list[dict]:
    """Vigencia, fecha de revisión e historial de cambios de cada trámite del catálogo."""
    return [
        {
            "id": clave,
            "nombre": ficha["nombre"],
            "codigo": ficha["codigo"],
            "fuente": ficha["fuente"],
            "vigencia": vigencia(ficha),
            "historial": ficha["historial"],
        }
        for clave, ficha in TRAMITES.items()
    ]

