"""Handlers de Telegram: el servidor único de api.py recibe o consulta los mensajes."""

import hashlib

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

import sesion
from asistente import responder
from config import settings


async def inicio(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """/start: lo primero que manda Telegram. Dice el número de chat para añadirlo a la lista."""
    chat = str(update.effective_chat.id)
    if chat in settings.permitidos:
        await update.message.reply_text("¡Hola! Ya puedes escribirme. Si quieres entrar a la web, pídeme /acceso por privado.")
    else:
        await update.message.reply_text(f"Tu número de chat es {chat}. Pídele al dueño del bot que lo añada.")


async def acceso(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Entrega un acceso temporal SOLO al chat privado autorizado; no llama al modelo."""
    chat = update.effective_chat
    if str(chat.id) not in settings.permitidos:
        await update.message.reply_text("No autorizado. Pídele al dueño del bot que agregue tu chat.")
        return
    if chat.type != "private":
        await update.message.reply_text("Por seguridad, pídeme /acceso en un chat privado conmigo.")
        return

    nombre = update.effective_user.first_name if update.effective_user else "Usuario"
    correo, password = sesion.emitir_acceso(chat.id, nombre)
    aviso = "No las compartas." if settings.acceso_fijo else "La contraseña se usa una vez y vence en 10 minutos."
    await update.message.reply_text(
        f"Datos de acceso a la web de TRAMIA:\nCorreo: {correo}\nContraseña: {password}\n\n"
        f"{aviso} Para volver a pedirlos, escribe /acceso."
    )


def pide_acceso(texto: str) -> bool:
    """También entiende una petición explícita de las credenciales del chat web."""
    texto = texto.casefold()
    canales = ("chat", "web", "interfaz", "login")
    solicitudes = ("acceso", "credenciales", "ingresar", "entrar", "iniciar sesión", "iniciar sesion")
    return (
        (any(solicitud in texto for solicitud in solicitudes) and any(canal in texto for canal in canales))
        or (any(nombre in texto for nombre in ("correo", "email", "usuario"))
            and any(clave in texto for clave in ("contraseña", "contrasena", "clave")))
    )


async def mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat = str(update.effective_chat.id)
    if chat not in settings.permitidos:  # se rechaza ANTES de llamar al modelo (y de gastar tu cuota)
        print(f"Chat no autorizado: {chat}", flush=True)
        await update.message.reply_text(f"No autorizado. Tu chat es {chat}: pídele al dueño que lo añada.")
        return
    if pide_acceso(update.message.text):
        await acceso(update, context)
        return
    try:
        respuesta = await responder(update.message.text)
    except Exception as error:  # cuota agotada (429), una API caída…: se avisa en vez de quedarse callado
        print("Error:", repr(error)[:300], flush=True)  # el detalle, en la terminal o en los Logs de Render
        respuesta = "Algo falló (el modelo o una herramienta). Intenta de nuevo en un minuto."
    await update.message.reply_text(respuesta[:4000])  # Telegram no acepta más de 4096 caracteres


def secreto_webhook() -> str:
    """El mismo secreto del webhook anterior: Telegram lo envía en cada POST."""
    token = settings.telegram_token.get_secret_value()
    return hashlib.sha256(token.encode()).hexdigest()[:32]


def crear_aplicacion(*, polling: bool = False) -> Application:
    """Registra los handlers sin abrir otro puerto; FastAPI gestiona su ciclo de vida."""
    token = settings.telegram_token.get_secret_value()
    if not token:
        raise ValueError("Falta TELEGRAM_TOKEN: ponlo en .env o en Environment de Render.")
    constructor = Application.builder().token(token)
    if not polling:
        constructor = constructor.updater(None)  # /telegram lo atiende FastAPI, no el servidor de PTB
    app = constructor.build()
    app.add_handler(CommandHandler("start", inicio))
    app.add_handler(CommandHandler("acceso", acceso))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, mensaje))
    return app
