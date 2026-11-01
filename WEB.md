# Extra opcional: la interfaz web

**No hace falta para el trabajo final.** Lo principal es el bot de Telegram del [README](README.md). Esto es la web de TRAMIA: React en `web/`, servida por el mismo `api.py`, con **login sin base de datos**.

Un solo servicio en Render alcanza: el build de React produce archivos estáticos que Python sirve, y el mismo `api.py` recibe el webhook de Telegram. Node no queda corriendo en producción.

```
GET  /                     la interfaz compilada (web/dist)
POST /api/auth/login       inicio de sesión
GET  /api/auth/me          ¿quién soy? (401 si no hay sesión)
POST /api/mvp/query        pregunta → respuesta + conversación completa
POST /telegram             webhook de Telegram (con encabezado secreto)
```

## 1 · Configura la sesión

1. Configura `TELEGRAM_TOKEN` y `TELEGRAM_PERMITIDOS` (ver [README](README.md#3--tu-bot-de-telegram)). Genera el secreto para firmar la sesión:

   ```bash
   uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. Pon ese valor en `.env`:

   ```
   SESION_SECRETO=el-token-que-salió
   COOKIE_SEGURA=false
   ```

   `SESION_SECRETO` es obligatorio cuando hay `TELEGRAM_TOKEN`. `COOKIE_SEGURA` es `false` en tu equipo (http) y `true` en Render (https).

## 2 · Pruébala en tu equipo

```bash
cd web
pnpm install       # solo la primera vez
pnpm build         # deja la interfaz en web/dist
cd ..
uv run uvicorn api:app --reload
```

Abre **http://127.0.0.1:8000**. Para probar también Telegram en tu equipo, pon `TELEGRAM_POLLING_LOCAL=true` en `.env` y reinicia uvicorn.

Si vas a cambiar la interfaz, trabaja con recarga en caliente: deja `uv run uvicorn api:app --reload` en una terminal y `cd web && pnpm dev` en otra. Vite (puerto 5173) manda `/api` a `http://localhost:8000` y tú abres http://127.0.0.1:5173.

El polling local borra el webhook del bot en Render: úsalo solo si no lo tienes desplegado o si vas a volver a registrar el webhook reiniciando Render después. Por defecto está desactivado.

> Sin `pnpm build`, la raíz `/` no existe pero la API y `/chat` siguen funcionando. Es a propósito: `api.py` solo monta la web si encuentra `web/dist`.

## 3 · Publícala en Render

Es el **único servicio** del repositorio: web, API y bot comparten el proceso de FastAPI. No crees otro servicio con el mismo `TELEGRAM_TOKEN`.

1. En [dashboard.render.com](https://dashboard.render.com): **+ New → Web Service** y elige el repositorio (o cambia el servicio del bot existente a estos comandos).
2. Completa estos campos:

   | Campo | Valor |
   |---|---|
   | **Name** | `tramia`. Será parte de la URL |
   | **Build Command** | `uv sync --locked --no-dev` |
   | **Start Command** | `uv run --no-sync uvicorn api:app --host 0.0.0.0 --port $PORT` |
   | **Instance Type** | **Free** |

   El build ya no compila la interfaz: `web/dist` va versionado, así que Render solo instala las dependencias de Python. No hace falta Node ni Docker.

3. En **Environment Variables**:

   | Key | Value |
   |---|---|
   | `DEEPSEEK_API_KEY` | Tu clave de DeepSeek |
   | `GEMINI_API_KEY_LOCAL` | Solo si vuelves a Gemini o usas el RAG |
   | `TELEGRAM_TOKEN` | Tu token de BotFather |
   | `TELEGRAM_PERMITIDOS` | Números de chat autorizados, separados por coma |
   | `SESION_SECRETO` | Un secreto largo (o **Generate** en Render) |
   | `COOKIE_SEGURA` | `true` |

4. Pulsa **Deploy Web Service** y abre `https://tramia.onrender.com`. En *Logs* busca `Webhook en https://tramia.onrender.com/telegram`. En Telegram prueba `/start`.

El servicio Free se duerme a los 15 minutos; el primer mensaje de Telegram o la primera visita a la web pueden tardar mientras despierta. Al reiniciar se pierden las conversaciones guardadas solo en memoria.

## 4 · Qué se guarda y qué no

| Se guarda | Dónde | Se pierde |
|---|---|---|
| Sesión | cookie del navegador y memoria del servidor | al reiniciar el servicio o al cerrar sesión |
| Conversaciones | memoria del proceso (`conversaciones.py`) | al reiniciar el servicio o al despertarse tras dormir |

Las conversaciones viven en memoria **a propósito**: sin base de datos no hay datos personales en reposo. El precio es que cada reinicio empieza con el historial vacío. Mantén **un solo worker de uvicorn**: varios workers tendrían historiales distintos y registrarían el mismo webhook varias veces. Si algún día necesitas historial permanente, eso ya es una base de datos y otra conversación sobre qué se guarda y por cuánto tiempo.

## 5 · Si algo falla

| Síntoma | Qué pasa |
|---|---|
| La raíz `/` da `404` | No existe `web/dist`: o no lo versionaste, o falta en el clon |
| Al arrancar: `falta SESION_SECRETO` | Hay `TELEGRAM_TOKEN` configurado sin secreto: agrégalo |
| Entra, pero al rato pide login otra vez | Se reinició el servicio o cambió `SESION_SECRETO` |
| Entra y todo está vacío | El servicio se reinició: las conversaciones viven en memoria |
| El chat responde `503` | Falló el modelo o una tool: mira la terminal o los *Logs* de Render (un `429` es cuota: la de Gemini es diaria y gratis, DeepSeek se paga por uso) |

## 6 · Pruebas

```bash
uv run pytest          # incluye login, cookie, conversaciones y la web servida
cd web && pnpm test    # la interfaz, con `fetch` simulado
```

Ninguna llama al modelo real ni gasta cuota.

## Cuidado

- El login protege la **interfaz**, no la API de programas: `POST /chat` sigue usando `API_TOKENS` (ver [API.md](API.md)). Son dos llaves distintas, a propósito.
- Si se filtra `SESION_SECRETO`, cámbialo: todas las sesiones abiertas dejan de valer.
