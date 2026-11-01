"""Las conversaciones de la interfaz web, en memoria del proceso (sin base de datos).

Se pierden cuando el servicio se reinicia: es el precio de no guardar nada. En Render,
cada reinicio o cada despertar del plan Free empieza con el historial vacío.
"""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic_ai.messages import ModelRequest, ModelResponse, TextPart, UserPromptPart

from asistente import responder

MAX_CONVERSACIONES = 50  # por usuario, para que la memoria no crezca sin control
MENSAJES_AL_MODELO = 20  # solo los últimos turnos vuelven al modelo (los tokens se pagan)

_CONVERSACIONES: dict[str, dict[str, dict]] = {}  # correo → id → conversación


def _ahora() -> str:
    """Fecha en el mismo formato que espera el navegador: 2026-10-31T12:00:00.000Z."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def _mensaje(rol: str, contenido: str) -> dict:
    return {"id": uuid4().hex, "role": rol, "content": contenido, "createdAt": _ahora()}


def _titulo(pregunta: str) -> str:
    return " ".join(pregunta.split())[:60] or "Nueva consulta"


def _historial(mensajes: list[dict]) -> list:
    """Convierte los mensajes guardados (texto) en el historial que espera Pydantic AI."""
    historial: list = []
    for mensaje in mensajes[-MENSAJES_AL_MODELO:]:
        if mensaje["role"] == "user":
            historial.append(ModelRequest(parts=[UserPromptPart(mensaje["content"])]))
        else:
            historial.append(ModelResponse(parts=[TextPart(mensaje["content"])]))
    return historial


def _del_usuario(correo: str) -> dict[str, dict]:
    return _CONVERSACIONES.setdefault(correo, {})


def listar(correo: str) -> list[dict]:
    """Las conversaciones más recientes primero, como las pinta la web."""
    return sorted(_del_usuario(correo).values(), key=lambda c: c["updatedAt"], reverse=True)


def borrar(correo: str, conversacion_id: str) -> bool:
    return _del_usuario(correo).pop(conversacion_id, None) is not None


def _buscar_o_crear(correo: str, pregunta: str, conversacion_id: str | None) -> dict:
    conversaciones = _del_usuario(correo)
    if conversacion_id and conversacion_id in conversaciones:
        return conversaciones[conversacion_id]

    # Si el id no existe (servicio reiniciado, conversación borrada) se abre una nueva.
    ahora = _ahora()
    conversacion = {
        "id": uuid4().hex,
        "title": _titulo(pregunta),
        "createdAt": ahora,
        "updatedAt": ahora,
        "messages": [],
    }
    conversaciones[conversacion["id"]] = conversacion

    if len(conversaciones) > MAX_CONVERSACIONES:  # se van las más viejas
        viejas = sorted(conversaciones.values(), key=lambda c: c["updatedAt"])
        for vieja in viejas[: len(conversaciones) - MAX_CONVERSACIONES]:
            conversaciones.pop(vieja["id"], None)
    return conversacion


async def preguntar(correo: str, pregunta: str, conversacion_id: str | None = None) -> dict:
    """Una pregunta entra, la respuesta sale y la conversación queda completa para la web."""
    conversacion = _buscar_o_crear(correo, pregunta, conversacion_id)
    respuesta = await responder(pregunta, _historial(conversacion["messages"]))

    conversacion["messages"].append(_mensaje("user", pregunta))
    conversacion["messages"].append(_mensaje("assistant", respuesta))
    conversacion["updatedAt"] = _ahora()
    return {"answer": respuesta, "conversation": conversacion}
