"""Servidor único para la web, la API y Telegram (instrucciones en README.md y WEB.md).

En tu equipo:  uv run uvicorn api:app --reload   →   http://127.0.0.1:8000
En Render, el mismo proceso también recibe el webhook de Telegram en /telegram.
"""

import os
import secrets
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import conversaciones
import bot
import sesion
from asistente import responder
from config import RAIZ, settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Arranca Telegram dentro de uvicorn; la web y el bot comparten un solo proceso."""
    app.state.telegram = None
    url = os.getenv("RENDER_EXTERNAL_URL")
    token = settings.telegram_token.get_secret_value()
    polling = settings.telegram_polling_local and not url
    if url and not token:
        raise RuntimeError("Falta TELEGRAM_TOKEN para registrar el webhook en Render.")
    if polling and not token:
        raise RuntimeError("Falta TELEGRAM_TOKEN para activar TELEGRAM_POLLING_LOCAL.")
    if not token or (not url and not polling):
        yield  # web y API sin Telegram: no tocan el webhook de Render
        return

    telegram = bot.crear_aplicacion(polling=polling)
    async with telegram:  # initialize() al entrar, shutdown() al salir
        try:
            if url:
                webhook = f"{url.rstrip('/')}/telegram"
                await telegram.bot.set_webhook(webhook, secret_token=bot.secreto_webhook())
                print(f"Webhook en {webhook} · permitidos: {sorted(settings.permitidos) or 'nadie'}", flush=True)
            else:
                # Solo con opt-in local: start_polling borra el webhook del bot en Render.
                await telegram.updater.start_polling()
                print(f"Telegram en polling local · permitidos: {sorted(settings.permitidos) or 'nadie'}", flush=True)

            await telegram.start()
            app.state.telegram = telegram
            yield
        finally:
            app.state.telegram = None
            if polling and telegram.updater.running:
                await telegram.updater.stop()
            if telegram.running:
                await telegram.stop()


app = FastAPI(title="TRAMIA", lifespan=lifespan)

WEB = RAIZ / "web" / "dist"  # lo que genera `pnpm build`; si no existe, no hay interfaz


def autenticar(credenciales: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False))) -> None:
    """Como TELEGRAM_PERMITIDOS: sin un token de API_TOKENS no se llama al modelo (ni se gasta tu cuota)."""
    token = credenciales.credentials if credenciales else ""
    # compare_digest compara sin dar pistas por el tiempo que tarda
    if not any(secrets.compare_digest(token, valido) for valido in settings.tokens):
        raise HTTPException(401, "Token inválido")


class Pedido(BaseModel):
    """Lo que manda el cliente. Pydantic lo valida: un mensaje vacío o enorme da 422 sin llamar al modelo."""

    mensaje: str = Field(min_length=1, max_length=2000)


class Respuesta(BaseModel):
    texto: str


@app.post("/chat", dependencies=[Depends(autenticar)])
async def chat(pedido: Pedido) -> Respuesta:
    return Respuesta(texto=await responder(pedido.mensaje))  # el mismo responder que usa el bot


@app.post("/telegram")
async def telegram_webhook(request: Request) -> dict:
    """Solo Telegram puede poner updates en la cola; los handlers aplican TELEGRAM_PERMITIDOS."""
    from telegram import Update

    telegram = getattr(request.app.state, "telegram", None)
    if telegram is None:
        raise HTTPException(503, "Telegram no está habilitado")
    recibido = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    if not secrets.compare_digest(recibido, bot.secreto_webhook()):
        raise HTTPException(403, "Webhook no autorizado")
    if len(await request.body()) > 1024 * 1024:
        raise HTTPException(413, "Update demasiado grande")
    try:
        datos = await request.json()
        if not isinstance(datos, dict):
            raise ValueError("Update inválido")
        update = Update.de_json(datos, telegram.bot)
        if update is None:
            raise ValueError("Update inválido")
    except (ValueError, TypeError):
        raise HTTPException(400, "Update inválido") from None
    await telegram.update_queue.put(update)
    return {"ok": True}


# ── Interfaz web: login sin base de datos + conversaciones en memoria ──


class Credenciales(BaseModel):
    """Lo que manda la pantalla de login."""

    email: str = Field(min_length=3, max_length=200)
    password: str = Field(min_length=1, max_length=200)


class Consulta(BaseModel):
    """Lo que manda el chat: la pregunta y, si continúa, la conversación abierta."""

    question: str = Field(min_length=1, max_length=2000)
    conversationId: str | None = None


@app.get("/api/health")
async def health() -> dict:
    """La web lo usa para mostrar «En línea» o «Sin conexión»."""
    return {"estado": "ok"}


@app.post("/api/auth/login")
async def login(datos: Credenciales, request: Request, respuesta: Response) -> dict:
    correo = datos.email.strip().lower()
    clave = f"{request.client.host if request.client else '?'}|{correo}"
    sesion.revisar_intentos(clave)

    if not sesion.usar_clave(correo, datos.password):
        sesion.anotar_fallo(clave)
        raise HTTPException(401, "Correo electrónico o contraseña incorrectos.")

    sesion.olvidar_intentos(clave)
    respuesta.set_cookie(
        sesion.COOKIE,
        sesion.crear_sesion(correo),
        max_age=sesion.DURACION,
        httponly=True,  # el JavaScript de la página no puede leer la cookie
        samesite="lax",  # no viaja en pedidos de otros sitios: frena el CSRF
        secure=settings.cookie_segura,  # True en Render (https)
        path="/",
    )
    return {"user": sesion.usuario_publico(correo)}


@app.post("/api/auth/logout")
async def logout(respuesta: Response) -> dict:
    respuesta.delete_cookie(sesion.COOKIE, path="/")
    return {"ok": True}


@app.get("/api/auth/me")
async def me(usuario: dict = Depends(sesion.usuario_actual)) -> dict:
    """Si la cookie vale, devuelve el usuario; si no, 401 y la web muestra el login."""
    return {"user": usuario}


@app.post("/api/mvp/query")
async def query(datos: Consulta, usuario: dict = Depends(sesion.usuario_actual)) -> dict:
    """Cada pregunta pasa por el mismo `responder` del bot, con el historial de esa conversación."""
    try:
        resultado = await conversaciones.preguntar(usuario["email"], datos.question, datos.conversationId)
    except Exception as error:  # cuota agotada (429), una tool caída…: la web muestra el aviso
        print("Error:", repr(error)[:300], flush=True)
        return JSONResponse({"detail": "El asistente no pudo responder. Intenta de nuevo en un minuto."}, 503)
    return resultado


@app.get("/api/mvp/conversations")
async def conversations(usuario: dict = Depends(sesion.usuario_actual)) -> list[dict]:
    return conversaciones.listar(usuario["email"])


@app.delete("/api/mvp/conversations/{conversacion_id}")
async def delete_conversation(conversacion_id: str, usuario: dict = Depends(sesion.usuario_actual)) -> dict:
    if not conversaciones.borrar(usuario["email"], conversacion_id):
        raise HTTPException(404, "Conversación no encontrada")
    return {"ok": True}


if WEB.is_dir():  # sin build no hay interfaz, pero la API sigue funcionando
    app.mount("/", StaticFiles(directory=WEB, html=True), name="web")
