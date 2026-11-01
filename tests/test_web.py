"""Pruebas de la interfaz web (WEB.md): login sin base de datos y conversaciones en memoria.

Sin modelo real ni red, igual que el resto: `uv run pytest`.
"""

import json
import os
import secrets
from types import SimpleNamespace

os.environ.setdefault("GEMINI_API_KEY_LOCAL", "clave-de-prueba")  # para importar sin .env
os.environ.setdefault("DEEPSEEK_API_KEY", "clave-de-prueba")  # igual, por si el .env usa MODO=deepseek

import httpx  # noqa: E402
import pytest  # noqa: E402
from pydantic import SecretStr  # noqa: E402
from pydantic_ai import ModelResponse, TextPart  # noqa: E402
from pydantic_ai.models.function import FunctionModel  # noqa: E402

import api  # noqa: E402
import asistente  # noqa: E402
import bot  # noqa: E402
import conversaciones  # noqa: E402
import sesion  # noqa: E402
from config import settings  # noqa: E402

USUARIO = "tg-123@tramia.local"


def responde(texto: str) -> FunctionModel:
    """Un modelo falso que siempre contesta lo mismo."""
    return FunctionModel(lambda mensajes, info: ModelResponse(parts=[TextPart(texto)]))


@pytest.fixture(autouse=True)
def usuario_de_prueba(monkeypatch):
    """Cada prueba arranca sin credenciales ni conversaciones guardadas."""
    monkeypatch.setattr(settings, "sesion_secreto", SecretStr("secreto-de-prueba"))
    monkeypatch.setattr(settings, "acceso_web", SecretStr(""))
    sesion._ACCESOS.clear()
    conversaciones._CONVERSACIONES.clear()
    sesion._INTENTOS.clear()


def otras_credenciales() -> tuple[str, str]:
    """Credenciales nuevas en cada prueba: nunca valores fijos que parezcan reales."""
    return f"{secrets.token_hex(4)}@ejemplo.test", secrets.token_urlsafe(12)


@pytest.fixture
def credenciales() -> tuple[str, str]:
    """Simula el único modo de obtener credenciales: /acceso en Telegram."""
    return sesion.emitir_acceso(123, "Estudiante de prueba")


@pytest.fixture
def acceso_configurado(monkeypatch) -> tuple[str, str]:
    """Configura ACCESO_WEB como en producción, con un correo y una clave al azar."""
    correo, clave = otras_credenciales()
    monkeypatch.setattr(settings, "acceso_web", SecretStr(f"{correo}:{clave}"))
    return correo, clave


def cliente() -> httpx.AsyncClient:
    """Habla con la app en el mismo proceso, sin servidor ni red."""
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url="http://prueba")


async def entrar(cliente_http: httpx.AsyncClient, credenciales: tuple[str, str]) -> None:
    correo, clave = credenciales
    respuesta = await cliente_http.post("/api/auth/login", json={"email": correo, "password": clave})
    assert respuesta.status_code == 200


# ── Login ──


async def test_login_correcto_deja_la_cookie_y_devuelve_el_usuario(credenciales):
    async with cliente() as c:
        respuesta = await c.post("/api/auth/login", json={"email": USUARIO.upper(), "password": credenciales[1]})
        assert respuesta.status_code == 200
        assert respuesta.json()["user"]["email"] == USUARIO
        assert "httponly" in respuesta.headers["set-cookie"].lower()

        perfil = await c.get("/api/auth/me")  # la cookie viaja sola en el cliente
        assert perfil.status_code == 200
        assert perfil.json()["user"]["displayName"] == "Estudiante de prueba"


async def test_login_incorrecto_no_devuelve_cookie(credenciales):
    async with cliente() as c:
        respuesta = await c.post("/api/auth/login", json={"email": USUARIO, "password": "otra"})
        assert respuesta.status_code == 401
        assert "set-cookie" not in respuesta.headers
        assert (await c.get("/api/auth/me")).status_code == 401


async def test_login_solo_acepta_claves_emitidas_por_telegram(monkeypatch):
    correo, clave = otras_credenciales()
    monkeypatch.setenv("USUARIOS", f"{correo}:hash-antiguo:Estudiante")
    async with cliente() as c:
        respuesta = await c.post("/api/auth/login", json={"email": correo, "password": clave})
    assert respuesta.status_code == 401  # la variable antigua ya no permite entrar


async def test_datos_pedidos_en_telegram_permiten_entrar_en_la_web(monkeypatch):
    monkeypatch.setattr(settings, "telegram_permitidos", "123")
    enviados = []

    async def reply_text(texto):
        enviados.append(texto)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        effective_user=SimpleNamespace(first_name="Estudiante"),
        message=SimpleNamespace(reply_text=reply_text),
    )
    await bot.acceso(update, None)
    correo = enviados[0].split("Correo: ")[1].splitlines()[0]
    password = enviados[0].split("Contraseña: ")[1].splitlines()[0]

    async with cliente() as c:
        respuesta = await c.post("/api/auth/login", json={"email": correo, "password": password})
        assert respuesta.status_code == 200
        assert (await c.get("/api/auth/me")).json()["user"]["displayName"] == "Estudiante"


async def test_las_credenciales_configuradas_se_entregan_y_funcionan(monkeypatch, acceso_configurado):
    monkeypatch.setattr(settings, "telegram_permitidos", "123")
    correo, clave = acceso_configurado
    enviados = []

    async def reply_text(texto):
        enviados.append(texto)

    update = SimpleNamespace(
        effective_chat=SimpleNamespace(id=123, type="private"),
        effective_user=SimpleNamespace(first_name="Estudiante"),
        message=SimpleNamespace(reply_text=reply_text),
    )
    await bot.acceso(update, None)
    assert f"Correo: {correo}" in enviados[-1]
    assert f"Contraseña: {clave}" in enviados[-1]

    async with cliente() as c:
        respuesta = await c.post(
            "/api/auth/login", json={"email": correo.upper(), "password": clave}
        )
        assert respuesta.status_code == 200
        assert (await c.get("/api/auth/me")).status_code == 200
        # sigue funcionando en un segundo ingreso: no se consume
        async with cliente() as otro:
            otra = await otro.post("/api/auth/login", json={"email": correo, "password": clave})
            assert otra.status_code == 200


async def test_las_credenciales_configuradas_rechazan_otra_clave(acceso_configurado):
    correo, _ = acceso_configurado
    async with cliente() as c:
        respuesta = await c.post("/api/auth/login", json={"email": correo, "password": "otra"})
    assert respuesta.status_code == 401


async def test_la_clave_solo_sirve_una_vez(credenciales):
    async with cliente() as c, cliente() as otro:
        await entrar(c, credenciales)
        repetido = await otro.post("/api/auth/login", json={"email": USUARIO, "password": credenciales[1]})
        assert repetido.status_code == 401
        assert (await c.get("/api/auth/me")).status_code == 200  # la cookie sigue válida


async def test_la_clave_vence_y_volver_a_pedirla_revoca_la_sesion(credenciales, monkeypatch):
    inicio = sesion.time.time()
    monkeypatch.setattr(sesion.time, "time", lambda: inicio + sesion.VIGENCIA_CLAVE + 1)
    async with cliente() as c:
        vencido = await c.post("/api/auth/login", json={"email": USUARIO, "password": credenciales[1]})
        assert vencido.status_code == 401

    correo, nueva_clave = sesion.emitir_acceso(123, "Estudiante de prueba")
    assert nueva_clave != credenciales[1]
    async with cliente() as c:
        await entrar(c, (correo, nueva_clave))
        sesion.emitir_acceso(123, "Estudiante de prueba")
        assert (await c.get("/api/auth/me")).status_code == 401


async def test_me_sin_sesion_responde_401():
    async with cliente() as c:
        assert (await c.get("/api/auth/me")).status_code == 401
        assert (await c.get("/api/mvp/conversations")).status_code == 401


async def test_logout_cierra_la_sesion(credenciales):
    async with cliente() as c:
        await entrar(c, credenciales)
        await c.post("/api/auth/logout")
        assert (await c.get("/api/auth/me")).status_code == 401


async def test_cookie_manipulada_no_sirve():
    correo, _ = otras_credenciales()
    # Contenido bien formado, pero con una firma que no sale de SESION_SECRETO.
    contenido = sesion._base64(json.dumps({"u": correo}, separators=(",", ":")).encode())
    assert sesion.leer_sesion(f"{contenido}.firma-falsa") is None
    assert sesion.leer_sesion(None) is None


async def test_demasiados_intentos_frena_antes_de_probar_la_clave(credenciales):
    async with cliente() as c:
        for _ in range(sesion.MAX_INTENTOS):
            assert (await c.post("/api/auth/login", json={"email": USUARIO, "password": "mala"})).status_code == 401
        bloqueado = await c.post("/api/auth/login", json={"email": USUARIO, "password": credenciales[1]})
        assert bloqueado.status_code == 429  # ni siquiera con la clave correcta
        assert "set-cookie" not in bloqueado.headers


# ── Conversaciones ──


async def test_consulta_sin_sesion_no_llama_al_modelo():
    def modelo_prohibido(mensajes, info):
        raise AssertionError("no debía llamarse al modelo")

    async with cliente() as c:
        with asistente.asistente.override(model=FunctionModel(modelo_prohibido)):
            respuesta = await c.post("/api/mvp/query", json={"question": "¿Qué necesito?"})
    assert respuesta.status_code == 401


async def test_consulta_con_sesion_guarda_la_conversacion(credenciales):
    async with cliente() as c:
        await entrar(c, credenciales)
        with asistente.asistente.override(model=responde("Pide el certificado de biblioteca.")):
            respuesta = await c.post("/api/mvp/query", json={"question": "¿Qué necesito para el diploma?"})

        assert respuesta.status_code == 200
        datos = respuesta.json()
        assert datos["answer"] == "Pide el certificado de biblioteca."
        conversacion = datos["conversation"]
        assert conversacion["title"] == "¿Qué necesito para el diploma?"
        assert [m["role"] for m in conversacion["messages"]] == ["user", "assistant"]

        listado = await c.get("/api/mvp/conversations")
        assert [c_["id"] for c_ in listado.json()] == [conversacion["id"]]


async def test_segunda_consulta_recibe_el_historial_anterior(credenciales):
    recibidos: list[str] = []

    def mira_el_historial(mensajes, info):
        recibidos.append(str(mensajes))
        return ModelResponse(parts=[TextPart("Otra respuesta.")])

    async with cliente() as c:
        await entrar(c, credenciales)
        with asistente.asistente.override(model=responde("Primera respuesta.")):
            primera = (await c.post("/api/mvp/query", json={"question": "Hola"})).json()["conversation"]["id"]
        with asistente.asistente.override(model=FunctionModel(mira_el_historial)):
            await c.post("/api/mvp/query", json={"question": "¿Y ahora?", "conversationId": primera})

    assert "Primera respuesta." in recibidos[-1]  # el turno anterior vuelve al modelo: recuerda


async def test_borrar_conversacion_la_quita_del_historial(credenciales):
    async with cliente() as c:
        await entrar(c, credenciales)
        with asistente.asistente.override(model=responde("Listo.")):
            creada = (await c.post("/api/mvp/query", json={"question": "Hola"})).json()["conversation"]["id"]

        assert (await c.delete(f"/api/mvp/conversations/{creada}")).status_code == 200
        assert (await c.get("/api/mvp/conversations")).json() == []
        assert (await c.delete(f"/api/mvp/conversations/{creada}")).status_code == 404


async def test_las_conversaciones_de_un_usuario_no_se_mezclan(credenciales):
    correo_otro, clave_otro = sesion.emitir_acceso(456, "Otro")
    async with cliente() as primero, cliente() as segundo:
        await entrar(primero, credenciales)
        await segundo.post("/api/auth/login", json={"email": correo_otro, "password": clave_otro})

        with asistente.asistente.override(model=responde("Hola.")):
            await primero.post("/api/mvp/query", json={"question": "Hola"})

        assert len((await primero.get("/api/mvp/conversations")).json()) == 1
        assert (await segundo.get("/api/mvp/conversations")).json() == []


# ── La interfaz compilada ──


@pytest.mark.skipif(not api.WEB.is_dir(), reason="falta `pnpm build` en web/")
async def test_la_web_compilada_se_sirve_desde_la_raiz():
    async with cliente() as c:
        respuesta = await c.get("/")
    assert respuesta.status_code == 200
    assert "text/html" in respuesta.headers["content-type"]
    assert "<div id=\"root\">" in respuesta.text


async def test_health_responde_sin_sesion():
    async with cliente() as c:
        assert (await c.get("/api/health")).json() == {"estado": "ok"}
