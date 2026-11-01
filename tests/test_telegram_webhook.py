"""Un solo servidor para la web y Telegram; pruebas sin red ni modelo real."""

import os
from types import SimpleNamespace
from unittest.mock import AsyncMock

os.environ.setdefault("GEMINI_API_KEY_LOCAL", "clave-de-prueba")
os.environ.setdefault("DEEPSEEK_API_KEY", "clave-de-prueba")  # por si el .env usa MODO=deepseek

import httpx  # noqa: E402
from pydantic import SecretStr  # noqa: E402

import api  # noqa: E402
import bot  # noqa: E402
from config import settings  # noqa: E402


def cliente() -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url="http://prueba")


class TelegramFalso:
    """Simula el ciclo de vida sin registrar el webhook ni llamar a Telegram."""

    def __init__(self, polling: bool = False):
        self.bot = SimpleNamespace(set_webhook=AsyncMock())
        self.updater = SimpleNamespace(start_polling=AsyncMock(), stop=AsyncMock(), running=polling)
        self.start = AsyncMock()
        self.stop = AsyncMock()
        self.running = True
        self.update_queue = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        pass


async def test_render_inicia_webhook_y_detiene_telegram_con_el_servidor(monkeypatch):
    falso = TelegramFalso()
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://tramia.onrender.com/")
    monkeypatch.setattr(settings, "telegram_token", SecretStr("123:prueba"))
    monkeypatch.setattr(bot, "crear_aplicacion", lambda *, polling: falso)

    async with api.lifespan(api.app):
        assert api.app.state.telegram is falso
        falso.bot.set_webhook.assert_awaited_once_with(
            "https://tramia.onrender.com/telegram", secret_token=bot.secreto_webhook()
        )
        falso.start.assert_awaited_once()
        falso.updater.start_polling.assert_not_awaited()

    falso.stop.assert_awaited_once()
    assert api.app.state.telegram is None


async def test_local_no_toca_telegram_sin_permiso_explicitamente_dado(monkeypatch):
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    monkeypatch.setattr(settings, "telegram_token", SecretStr("123:prueba"))
    monkeypatch.setattr(settings, "telegram_polling_local", False)
    monkeypatch.setattr(bot, "crear_aplicacion", lambda **_: (_ for _ in ()).throw(AssertionError("no iniciar")))

    async with api.lifespan(api.app):
        assert api.app.state.telegram is None


async def test_polling_local_se_activa_solo_con_opt_in(monkeypatch):
    falso = TelegramFalso(polling=True)
    monkeypatch.delenv("RENDER_EXTERNAL_URL", raising=False)
    monkeypatch.setattr(settings, "telegram_token", SecretStr("123:prueba"))
    monkeypatch.setattr(settings, "telegram_polling_local", True)
    monkeypatch.setattr(bot, "crear_aplicacion", lambda *, polling: falso if polling else None)

    async with api.lifespan(api.app):
        falso.updater.start_polling.assert_awaited_once()
        falso.bot.set_webhook.assert_not_awaited()

    falso.updater.stop.assert_awaited_once()
    falso.stop.assert_awaited_once()


async def test_render_sin_token_falla_al_arrancar(monkeypatch):
    monkeypatch.setenv("RENDER_EXTERNAL_URL", "https://tramia.onrender.com")
    monkeypatch.setattr(settings, "telegram_token", SecretStr(""))
    try:
        async with api.lifespan(api.app):
            assert False, "No debe arrancar sin token"
    except RuntimeError as error:
        assert "TELEGRAM_TOKEN" in str(error)


async def test_webhook_no_acepta_actualizaciones_sin_secreto(monkeypatch):
    monkeypatch.setattr(settings, "telegram_token", SecretStr("123:prueba"))
    api.app.state.telegram = bot.crear_aplicacion()
    try:
        async with cliente() as c:
            for headers in ({}, {"X-Telegram-Bot-Api-Secret-Token": "falso"}):
                respuesta = await c.post("/telegram", json={"update_id": 1}, headers=headers)
                assert respuesta.status_code == 403
            assert api.app.state.telegram.update_queue.empty()
    finally:
        api.app.state.telegram = None


async def test_webhook_autorizado_pone_el_update_en_cola(monkeypatch):
    monkeypatch.setattr(settings, "telegram_token", SecretStr("123:prueba"))
    api.app.state.telegram = bot.crear_aplicacion()
    headers = {"X-Telegram-Bot-Api-Secret-Token": bot.secreto_webhook()}
    try:
        async with cliente() as c:
            assert (await c.post("/telegram", json=[], headers=headers)).status_code == 400
            assert (await c.post("/telegram", content=b"no es json", headers=headers)).status_code == 400
            respuesta = await c.post("/telegram", json={"update_id": 7}, headers=headers)
            assert respuesta.status_code == 200
            assert respuesta.json() == {"ok": True}
            assert api.app.state.telegram.update_queue.get_nowait().update_id == 7
    finally:
        api.app.state.telegram = None


async def test_webhook_inactivo_no_acepta_pedidos():
    api.app.state.telegram = None
    async with cliente() as c:
        assert (await c.post("/telegram", json={"update_id": 1})).status_code == 503
