"""Pruebas sin modelo real ni internet: uv run pytest

Un modelo falso (FunctionModel) pide la tool que queremos, y comprobamos lo que hace el código.
"""

import os
from datetime import date
from types import SimpleNamespace

os.environ.setdefault("GEMINI_API_KEY_LOCAL", "clave-de-prueba")  # para importar sin .env (no se llama a Gemini)
os.environ.setdefault("DEEPSEEK_API_KEY", "clave-de-prueba")  # igual, por si el .env usa MODO=deepseek

import httpx  # noqa: E402
from pydantic import SecretStr  # noqa: E402
from pydantic_ai import ModelResponse, TextPart, ToolCallPart, ToolReturnPart  # noqa: E402
from pydantic_ai.models.function import FunctionModel  # noqa: E402

import api  # noqa: E402
import asistente  # noqa: E402
import bot  # noqa: E402
import capacidades  # noqa: E402
import sesion  # noqa: E402
from config import settings  # noqa: E402


def pide(tool: str, args: dict) -> FunctionModel:
    """Un modelo falso: la 1.ª vez pide la tool; cuando recibe su resultado, responde texto."""

    def responder(mensajes, info):
        ultimo = mensajes[-1].parts[-1]
        if isinstance(ultimo, ToolReturnPart):
            return ModelResponse(parts=[TextPart(f"Resultado: {ultimo.content}")])
        return ModelResponse(parts=[ToolCallPart(tool, args)])

    return FunctionModel(responder)


# ── TRAMIA: el catálogo de trámites ──


def test_listar_tramites():
    tramites = capacidades.listar_tramites()
    assert {t["id"] for t in tramites} == {"diploma_academico", "titulo_profesional"}
    assert all(t["fuente"].startswith("https://titulos.umsa.bo/") for t in tramites)


def test_diploma_academico_no_tiene_requisitos_condicionados():
    ficha = capacidades.consultar_tramite("diploma_academico")
    assert ficha["por_confirmar"] == []
    assert len(ficha["requisitos_obligatorios"]) == 9
    assert ficha["costos_bs"][1] == {"concepto": "Nacionales, Licenciatura", "monto_bs": 1343}


def test_titulo_sin_datos_pide_confirmar_las_condiciones():
    ficha = capacidades.consultar_tramite("titulo_profesional")
    assert ficha["por_confirmar"] == ["carrera", "excelencia_academica", "nacionalidad"]
    assert ficha["requisitos_condicionales"] == []


def test_titulo_con_condiciones_agrega_sus_requisitos():
    ficha = capacidades.consultar_tramite(
        "titulo_profesional", nacionalidad="extranjera", carrera="medicina", excelencia_academica=True
    )
    assert ficha["por_confirmar"] == []
    condicionales = " ".join(ficha["requisitos_condicionales"])
    assert "consulado boliviano" in condicionales
    assert "Salud Rural Obligatorio" in condicionales
    assert "Record Académico" in condicionales


def test_tramite_fuera_del_catalogo_devuelve_error():
    assert "error" in capacidades.consultar_tramite("otro")  # type: ignore[arg-type]


# ── TRAMIA: la lista de verificación (BR-014 y BR-015) ──


def test_revisar_requisitos_marca_cumplidos_y_pendientes():
    ficha = capacidades.revisar_requisitos("diploma_academico", ["certificado de biblioteca", "las fotos"])
    assert len(ficha["cumplidos"]) == 2
    assert any("Biblioteca Central" in c for c in ficha["cumplidos"])
    assert any("fotografías" in c for c in ficha["cumplidos"])
    assert len(ficha["pendientes"]) == 7


def test_revisar_requisitos_no_da_por_bueno_lo_que_no_reconoce():
    ficha = capacidades.revisar_requisitos("diploma_academico", ["carta de recomendación"])
    assert ficha["cumplidos"] == []
    assert ficha["no_reconocidos"] == ["carta de recomendación"]
    assert "no está verificado" in ficha["aviso"]


def test_revisar_requisitos_entiende_las_negaciones():
    ficha = capacidades.revisar_requisitos("diploma_academico", ["no tengo el certificado de biblioteca"])
    assert ficha["cumplidos"] == []
    assert ficha["no_reconocidos"] == []  # una ausencia no es un documento por reconocer
    assert len(ficha["pendientes"]) == 9


def test_revisar_titulo_sin_datos_deja_los_condicionales_desconocidos():
    ficha = capacidades.revisar_requisitos("titulo_profesional", [])
    assert set(ficha["por_confirmar"]) == {"carrera", "excelencia_academica", "nacionalidad"}
    assert len(ficha["desconocidos"]) == 5  # un condicional por cada dato que falta
    assert len(ficha["pendientes"]) == 5  # los cinco requisitos obligatorios


def test_revisar_titulo_con_condiciones_clasifica_el_condicional():
    ficha = capacidades.revisar_requisitos(
        "titulo_profesional",
        ["servicio social"],
        nacionalidad="boliviana",
        carrera="medicina",
        excelencia_academica=False,
    )
    assert ficha["por_confirmar"] == []
    assert ficha["desconocidos"] == []
    assert any("Salud Rural" in c for c in ficha["cumplidos"])
    assert len(ficha["pendientes"]) == 5


def test_revisar_tramite_fuera_del_catalogo_devuelve_error():
    assert "error" in capacidades.revisar_requisitos("otro", [])  # type: ignore[arg-type]


async def test_el_agente_arma_la_lista_de_verificacion():
    modelo = pide("revisar_requisitos", {"tramite": "diploma_academico", "tengo": ["biblioteca"]})
    with asistente.asistente.override(model=modelo):
        respuesta = await asistente.responder("Ya tengo el certificado de biblioteca, ¿qué me falta?")
    assert "Biblioteca Central" in respuesta


# ── TRAMIA: dependencias entre trámites (BR-017 y BR-018) ──


def test_el_titulo_requiere_el_diploma_primero():
    ficha = capacidades.consultar_dependencias("titulo_profesional")
    assert ficha["orden"] == ["diploma_academico", "titulo_profesional"]
    assert ficha["requiere_antes"][0]["tramite"] == "diploma_academico"
    assert "Legalizar" in ficha["requiere_antes"][0]["paso_previo"]


def test_el_diploma_no_tiene_dependencias():
    ficha = capacidades.consultar_dependencias("diploma_academico")
    assert ficha["requiere_antes"] == []
    assert ficha["orden"] == ["diploma_academico"]


def test_dependencias_de_un_tramite_desconocido():
    assert "error" in capacidades.consultar_dependencias("otro")  # type: ignore[arg-type]


def test_consultar_tramite_avisa_que_requiere_el_diploma():
    assert capacidades.consultar_tramite("titulo_profesional")["requiere_antes"] == ["diploma_academico"]


# ── TRAMIA: vigencia e historial (BR-005 y BR-025) ──


def test_vigencia_es_vigente_dentro_de_los_180_dias():
    ficha = capacidades.TRAMITES["diploma_academico"]
    assert capacidades.vigencia(ficha, dia=date(2026, 12, 1))["estado"] == "vigente"


def test_vigencia_pide_revision_pasados_180_dias():
    ficha = capacidades.TRAMITES["diploma_academico"]
    estado = capacidades.vigencia(ficha, dia=date(2027, 6, 1))
    assert estado["estado"] == "por_verificar"
    assert estado["dias_sin_revisar"] > capacidades.VIGENCIA_DIAS
    assert "confirma en el canal oficial" in estado["aviso"]


def test_vigencia_respeta_la_marca_humana_de_desactualizado():
    ficha = {**capacidades.TRAMITES["titulo_profesional"], "estado": "desactualizado"}
    assert capacidades.vigencia(ficha, dia=date(2026, 11, 1))["estado"] == "desactualizado"


def test_estado_catalogo_trae_vigencia_e_historial():
    fichas = capacidades.estado_catalogo()
    assert {f["id"] for f in fichas} == {"diploma_academico", "titulo_profesional"}
    for ficha in fichas:
        assert ficha["historial"][0]["fecha"] == "2026-10-31"
        assert ficha["vigencia"]["estado"] in {"vigente", "por_verificar", "desactualizado"}


async def test_el_agente_explica_el_orden_de_los_tramites():
    modelo = pide("consultar_dependencias", {"tramite": "titulo_profesional"})
    with asistente.asistente.override(model=modelo):
        respuesta = await asistente.responder("¿Puedo sacar el título sin el diploma?")
    assert "Diploma Académico" in respuesta


async def test_el_agente_informa_la_vigencia_del_catalogo():
    with asistente.asistente.override(model=pide("estado_catalogo", {})):
        respuesta = await asistente.responder("¿La información está actualizada?")
    assert "2026-10-31" in respuesta  # la fecha de revisión sale siempre; el estado depende del día


async def test_el_agente_consulta_el_catalogo():
    with asistente.asistente.override(model=pide("consultar_tramite", {"tramite": "titulo_profesional"})):
        respuesta = await asistente.responder("¿Qué necesito para el título profesional?")
    assert "R-271" in respuesta


# ── El bot: la lista de permitidos ──


async def test_chat_ajeno_se_rechaza_sin_llamar_al_modelo(monkeypatch):
    monkeypatch.setattr(settings, "telegram_permitidos", "123")
    respuestas = []

    async def reply_text(texto):
        respuestas.append(texto)

    def modelo_prohibido(mensajes, info):
        raise AssertionError("no debía llamarse al modelo")

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=999), message=SimpleNamespace(text="hola", reply_text=reply_text)
    )
    with asistente.asistente.override(model=FunctionModel(modelo_prohibido)):
        await bot.mensaje(update, None)
    assert "No autorizado" in respuestas[0] and "999" in respuestas[0]


async def test_acceso_solo_se_entrega_en_chat_privado_autorizado(monkeypatch):
    monkeypatch.setattr(settings, "telegram_permitidos", "123, -456")
    monkeypatch.setattr(settings, "acceso_web", SecretStr(""))
    sesion._ACCESOS.clear()
    respuestas = []

    async def reply_text(texto):
        respuestas.append(texto)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=999, type="private"),
        effective_user=SimpleNamespace(first_name="Ana"),
        message=SimpleNamespace(reply_text=reply_text),
    )
    await bot.acceso(update, None)
    assert "No autorizado" in respuestas[-1]
    assert sesion._ACCESOS == {}

    update.effective_chat = SimpleNamespace(id=-456, type="group")
    await bot.acceso(update, None)
    assert "chat privado" in respuestas[-1]
    assert sesion._ACCESOS == {}

    update.effective_chat = SimpleNamespace(id=123, type="private")
    await bot.acceso(update, None)
    assert "Correo: tg-123@tramia.local" in respuestas[-1]
    assert "Contraseña:" in respuestas[-1]
    assert "tg-123@tramia.local" in sesion._ACCESOS
    assert respuestas[-1].split("Contraseña: ")[1].splitlines()[0] not in str(sesion._ACCESOS)


async def test_pedir_credenciales_en_lenguaje_natural_no_llama_al_modelo(monkeypatch):
    monkeypatch.setattr(settings, "telegram_permitidos", "123")
    monkeypatch.setattr(settings, "acceso_web", SecretStr(""))
    sesion._ACCESOS.clear()
    respuestas = []

    async def reply_text(texto):
        respuestas.append(texto)

    def modelo_prohibido(mensajes, info):
        raise AssertionError("no debía llamarse al modelo")

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        effective_user=SimpleNamespace(first_name="Ana"),
        message=SimpleNamespace(text="Dame el correo y contraseña del chat", reply_text=reply_text),
    )
    with asistente.asistente.override(model=FunctionModel(modelo_prohibido)):
        await bot.mensaje(update, None)
    assert "Correo: tg-123@tramia.local" in respuestas[-1]
    assert bot.pide_acceso("¿Me das el email y la clave para ingresar a la web?")
    assert bot.pide_acceso("Necesito iniciar sesión en el chat UI")
    assert not bot.pide_acceso("¿Qué necesito para el Diploma Académico?")


def test_permitidos(monkeypatch):
    monkeypatch.setattr(settings, "telegram_permitidos", " 123, 456 ,")
    assert settings.permitidos == {"123", "456"}
    monkeypatch.setattr(settings, "telegram_permitidos", "")
    assert settings.permitidos == set()  # vacío = nadie


# ── Extra opcional: la API (API.md) ──


async def post_chat(cuerpo: dict, token: str | None = None) -> httpx.Response:
    """Llama a la API en el mismo proceso, sin servidor ni red."""
    cabeceras = {"Authorization": f"Bearer {token}"} if token else {}
    transporte = httpx.ASGITransport(app=api.app)
    async with httpx.AsyncClient(transport=transporte, base_url="http://prueba") as cliente:
        return await cliente.post("/chat", json=cuerpo, headers=cabeceras)


async def test_api_sin_token_valido_no_llama_al_modelo(monkeypatch):
    def modelo_prohibido(mensajes, info):
        raise AssertionError("no debía llamarse al modelo")

    with asistente.asistente.override(model=FunctionModel(modelo_prohibido)):
        monkeypatch.setattr(settings, "api_tokens", SecretStr(""))
        assert (await post_chat({"mensaje": "hola"}, "cualquiera")).status_code == 401  # vacío = nadie
        monkeypatch.setattr(settings, "api_tokens", SecretStr("abc, def"))
        assert (await post_chat({"mensaje": "hola"})).status_code == 401
        assert (await post_chat({"mensaje": "hola"}, "xyz")).status_code == 401
        assert (await post_chat({"mensaje": ""}, "abc")).status_code == 422  # Pydantic valida el pedido


async def test_api_con_token_responde(monkeypatch):
    monkeypatch.setattr(settings, "api_tokens", SecretStr("abc,def"))
    with asistente.asistente.override(model=pide("consultar_tramite", {"tramite": "diploma_academico"})):
        r = await post_chat({"mensaje": "¿Qué necesito para el diploma académico?"}, "def")
    assert r.status_code == 200
    assert "Diploma Académico" in r.json()["texto"]
