"""Login sin base de datos para la interfaz web (instrucciones en WEB.md).

Dos ideas, sin dependencias nuevas:

1. Solo Telegram entrega una contraseña temporal; en memoria se guarda su hash lento
   (PBKDF2-SHA256), no la contraseña. Cada contraseña se usa una sola vez.
2. La cookie no se puede falsificar porque lleva una firma HMAC hecha con SESION_SECRETO.
   Si alguien cambia el correo dentro de la cookie, la firma deja de coincidir.
"""

import base64
import hashlib
import hmac
import json
import secrets
import time
from binascii import Error as Base64Error
from dataclasses import dataclass

from fastapi import Cookie, HTTPException

from config import settings

COOKIE = "sesion"
DURACION = 8 * 3600  # la sesión dura 8 horas
VIGENCIA_CLAVE = 10 * 60  # hay 10 minutos para entrar; luego hay que volver a pedir /acceso
ITERACIONES = 260_000  # cuantas más, más lento adivinar la contraseña (y más lento el login)


@dataclass
class Acceso:
    hash: str | None
    nombre: str
    nonce: str  # emitir otra clave invalida las sesiones anteriores de ese chat
    vence_clave: float
    vence_cuenta: float


_ACCESOS: dict[str, Acceso] = {}  # correo temporal → hash y vigencia; se pierde al reiniciar

# Intentos fallidos por correo e IP, en memoria. Frena la fuerza bruta sin base de datos.
_INTENTOS: dict[str, list[float]] = {}
MAX_INTENTOS = 5
VENTANA = 300  # segundos


def hash_password(password: str) -> str:
    """Convierte una contraseña en algo que se puede guardar: pbkdf2_sha256$iteraciones$sal$hash."""
    sal = secrets.token_bytes(16)
    derivado = hashlib.pbkdf2_hmac("sha256", password.encode(), sal, ITERACIONES)
    return f"pbkdf2_sha256${ITERACIONES}${sal.hex()}${derivado.hex()}"


def verificar_password(password: str, guardado: str) -> bool:
    """Compara sin dar pistas por el tiempo que tarda (compare_digest)."""
    try:
        algoritmo, iteraciones, sal_hex, hash_hex = guardado.split("$")
    except ValueError:
        return False
    if algoritmo != "pbkdf2_sha256":
        return False
    derivado = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(sal_hex), int(iteraciones))
    return hmac.compare_digest(derivado.hex(), hash_hex)


def _base64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode().rstrip("=")


def _firma(contenido: str) -> str:
    secreto = settings.sesion_secreto.get_secret_value()
    return _base64(hmac.new(secreto.encode(), contenido.encode(), hashlib.sha256).digest())


def emitir_acceso(chat_id: int, nombre: str) -> tuple[str, str]:
    """Solo lo llama el handler /acceso después de validar chat autorizado y privado."""
    fijo = settings.acceso_fijo
    if fijo:
        return fijo  # credenciales configuradas: se entregan siempre las mismas
    ahora = time.time()
    for correo, acceso in list(_ACCESOS.items()):
        if acceso.vence_cuenta < ahora:
            _ACCESOS.pop(correo, None)
    correo = f"tg-{chat_id}@tramia.local"  # no requiere un correo personal real
    password = secrets.token_urlsafe(18)
    _ACCESOS[correo] = Acceso(
        hash=hash_password(password),
        nombre=nombre,
        nonce=secrets.token_urlsafe(16),
        vence_clave=ahora + VIGENCIA_CLAVE,
        vence_cuenta=ahora + VIGENCIA_CLAVE,
    )
    return correo, password


def usar_clave(correo: str, password: str) -> bool:
    """La contraseña se consume al entrar; la sesión firmada sigue viva 8 horas."""
    fijo = settings.acceso_fijo
    if fijo and hmac.compare_digest(correo, fijo[0]) and hmac.compare_digest(password, fijo[1]):
        _ACCESOS.setdefault(
            correo,
            Acceso(
                hash=None,
                nombre=correo.split("@")[0].capitalize(),
                nonce=secrets.token_urlsafe(16),
                vence_clave=float("inf"),
                vence_cuenta=float("inf"),
            ),
        )
        return True

    acceso = _ACCESOS.get(correo)
    ahora = time.time()
    if not acceso or not acceso.hash or acceso.vence_clave < ahora:
        return False
    if not verificar_password(password, acceso.hash):
        return False
    acceso.hash = None
    acceso.vence_cuenta = ahora + DURACION
    return True


def crear_sesion(correo: str) -> str:
    """El valor de la cookie: datos firmados. No lleva la contraseña ni nada secreto."""
    datos = {"u": correo, "v": _ACCESOS[correo].nonce, "exp": int(time.time()) + DURACION}
    contenido = _base64(json.dumps(datos, separators=(",", ":")).encode())
    return f"{contenido}.{_firma(contenido)}"


def leer_sesion(valor: str | None) -> str | None:
    """Devuelve el correo de la cookie, o None si falta, está vencida o la firma no coincide."""
    if not valor or "." not in valor:
        return None
    contenido, _, firma = valor.rpartition(".")
    if not hmac.compare_digest(firma, _firma(contenido)):
        return None
    try:
        datos = json.loads(base64.urlsafe_b64decode(contenido + "=" * (-len(contenido) % 4)))
        if not isinstance(datos, dict) or int(datos.get("exp", 0)) < time.time():
            return None
    except (ValueError, TypeError, Base64Error):
        return None
    correo = str(datos.get("u", "")).lower()
    acceso = _ACCESOS.get(correo)
    return correo if acceso and acceso.vence_cuenta >= time.time() and datos.get("v") == acceso.nonce else None


def revisar_intentos(clave: str) -> None:
    """Si ya falló 5 veces en 5 minutos, se corta ANTES de probar la contraseña."""
    ahora = time.time()
    intentos = [instante for instante in _INTENTOS.get(clave, []) if ahora - instante < VENTANA]
    _INTENTOS[clave] = intentos
    if len(intentos) >= MAX_INTENTOS:
        raise HTTPException(429, "Demasiados intentos fallidos. Espera unos minutos.")


def anotar_fallo(clave: str) -> None:
    _INTENTOS.setdefault(clave, []).append(time.time())


def olvidar_intentos(clave: str) -> None:
    _INTENTOS.pop(clave, None)


def usuario_publico(correo: str) -> dict:
    """Lo que ve el navegador: nunca la contraseña ni su hash."""
    nombre = _ACCESOS[correo].nombre
    return {
        "id": hashlib.sha256(correo.encode()).hexdigest()[:16],  # estable, sin base de datos
        "displayName": nombre,
        "email": correo,
        "roles": ["orientador"],
        "permissions": ["consulta"],
        "scope": {},
    }


def usuario_actual(sesion: str | None = Cookie(default=None)) -> dict:
    """Dependencia de FastAPI: sin cookie válida responde 401 y no se llama al modelo."""
    correo = leer_sesion(sesion)
    if correo is None:
        raise HTTPException(401, "Sesión no válida o vencida")
    return usuario_publico(correo)
