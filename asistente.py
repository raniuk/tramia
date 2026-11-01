"""El agente: modelo + instrucciones + capabilities. Sin memoria: cada mensaje empieza de cero.

Pruébalo en la terminal, sin Telegram:  uv run asistente.py
"""

import asyncio

from pydantic_ai import Agent
from pydantic_ai.messages import ModelMessage

from capacidades import tramites
from config import modelo
asistente = Agent(
    modelo,
    # ← El asistente de TRAMIA: para quién es, qué hace y qué NO hace.
    instructions=(
        "Eres TRAMIA, un orientador de trámites académicos de la Universidad Mayor de San Andrés (UMSA). "
        "Ayudas a estudiantes, egresados y titulados a entender requisitos, costos, pasos y canales oficiales "
        "de la División de Títulos y Diplomas. "
        "Responde en español, breve y en texto plano (sin Markdown). "
        "Usa las tools del catálogo: no respondas requisitos, costos ni plazos de memoria. "
        "Si falta un dato que cambia los requisitos (nacionalidad, carrera o excelencia académica), pregúntalo antes de responder. "
        "Cita la fuente oficial y di cuándo se revisó el catálogo. "
        "Si el trámite no está en el catálogo, dilo; no lo inventes. "
        "Aclara que eres un prototipo independiente: das orientación, no una confirmación oficial, "
        "y no realizas el trámite ni emites documentos."
    ),
    capabilities=[tramites],  # ← aquí se conectan tus capabilities
)


async def responder(mensaje: str, historial: list[ModelMessage] | None = None) -> str:
    """Lo único que necesitan el bot y la web: un mensaje entra, una respuesta sale.

    `historial` es opcional: el bot lo deja vacío (cada mensaje empieza de cero) y la web
    manda los turnos anteriores para que el asistente recuerde la conversación.
    """
    resultado = await asistente.run(mensaje, message_history=historial)
    return resultado.output


async def main() -> None:
    while (mensaje := input("tú> ").strip()) not in {"", "salir"}:
        print("asistente>", await responder(mensaje))


if __name__ == "__main__":
    asyncio.run(main())  # un solo asyncio.run: todo lo async vive dentro
