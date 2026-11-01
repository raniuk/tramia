"""La configuración (del .env en tu equipo, o del panel Environment en Render) y el modelo.

En cualquier archivo:

    from config import modelo, settings
"""

from pathlib import Path
from typing import Literal

import pydantic_ai
from pydantic import SecretStr, model_validator
from pydantic_ai.models import Model
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.deepseek import DeepSeekProvider
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.ollama import OllamaProvider
from pydantic_settings import BaseSettings, SettingsConfigDict

pydantic_ai.BANNER_ENABLED = False  # sin el aviso de Logfire en cada ejecución

RAIZ = Path(__file__).resolve().parent  # la carpeta del proyecto
DATOS = RAIZ / "datos"  # gastos.csv y documentos/*.pdf


class Settings(BaseSettings):
    """pydantic-settings lee el .env (o las variables de Render) y valida cada una con su tipo."""

    # extra="ignore": si tu .env trae otras variables, no pasa nada
    model_config = SettingsConfigDict(env_file=RAIZ / ".env", extra="ignore")

    modo: Literal["gemini", "local", "deepseek"] = "deepseek"  # gemini = la nube · local = Ollama (no funciona en Render) · deepseek = la nube
    gemini_api_key_local: SecretStr = SecretStr("")  # SecretStr no se imprime por accidente
    gemini_model: str = "gemini-3.5-flash-lite"
    ollama_model: str = "gemma4:e2b"
    deepseek_api_key: SecretStr = SecretStr("")  # clave de https://platform.deepseek.com
    deepseek_model: str = "deepseek-chat"  # no uses deepseek-reasoner: agrega latencia al bot
    telegram_token: SecretStr = SecretStr("")  # el token de @BotFather
    telegram_permitidos: str = ""  # números de chat separados por coma; vacío = nadie
    telegram_polling_local: bool = False  # opt-in: probar el bot en el servidor local borra el webhook de Render

    api_tokens: SecretStr = SecretStr("")  # extra opcional (API.md): tokens de la API separados por coma; vacío = nadie

    # Interfaz web (WEB.md): Telegram entrega claves temporales; aquí solo va el secreto de las cookies.
    sesion_secreto: SecretStr = SecretStr("")
    cookie_segura: bool = False  # True en Render (https); False en tu equipo (http)
    acceso_web: SecretStr = SecretStr("")  # "correo:contraseña" que el bot entrega a pedido

    @property
    def permitidos(self) -> set[str]:
        return {c.strip() for c in self.telegram_permitidos.split(",") if c.strip()}

    @property
    def tokens(self) -> set[str]:
        return {t.strip() for t in self.api_tokens.get_secret_value().split(",") if t.strip()}

    @property
    def acceso_fijo(self) -> tuple[str, str] | None:
        """Credenciales que se entregan por Telegram: correo y contraseña, sin hash de por medio."""
        correo, _, password = self.acceso_web.get_secret_value().strip().partition(":")
        correo, password = correo.strip().lower(), password.strip()
        return (correo, password) if correo and password else None

    @model_validator(mode="after")
    def _clave_del_modo(self) -> "Settings":
        """Cada modo en la nube necesita su propia clave; Ollama es local y no lleva."""
        claves = {"gemini": self.gemini_api_key_local, "deepseek": self.deepseek_api_key}
        if self.modo in claves and not claves[self.modo].get_secret_value():
            raise ValueError(f"Falta la clave para MODO={self.modo} (ver .env.example).")
        return self

    @model_validator(mode="after")
    def _secreto_obligatorio(self) -> "Settings":
        """Un bot que emite accesos necesita un secreto para firmar la sesión web."""
        if self.telegram_token.get_secret_value() and not self.sesion_secreto.get_secret_value():
            raise ValueError("Hay TELEGRAM_TOKEN configurado: falta SESION_SECRETO (ver WEB.md).")
        return self


def crear_modelo(settings: Settings) -> Model:
    """El modelo de lenguaje, según el MODO."""
    if settings.modo == "local":
        # Ollama expone una API compatible con la de OpenAI en el puerto 11434
        provider = OllamaProvider(base_url="http://localhost:11434/v1")
        return OpenAIChatModel(settings.ollama_model, provider=provider)

    if settings.modo == "deepseek":
        # DeepSeek habla la misma API que OpenAI; solo cambia el proveedor
        provider = DeepSeekProvider(api_key=settings.deepseek_api_key.get_secret_value())
        return OpenAIChatModel(settings.deepseek_model, provider=provider)

    provider = GoogleProvider(api_key=settings.gemini_api_key_local.get_secret_value())
    return GoogleModel(settings.gemini_model, provider=provider)


settings = Settings()
modelo = crear_modelo(settings)
