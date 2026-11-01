# TRAMIA · Asistente de trámites de la UMSA

Prototipo de orientación sobre trámites de la **Universidad Mayor de San Andrés (UMSA)**, construido sobre la plantilla del trabajo final del curso **«Más allá de los chatbots»** de Alex Ojeda Copa, con [Pydantic AI](https://pydantic.dev/docs/ai/) y un **bot de Telegram** pensado para desplegarse gratis en **Render**.

## Qué hace este MVP

Orienta en lenguaje natural sobre dos trámites de la **División de Títulos y Diplomas**, con datos de sus páginas oficiales (gestión 2026) revisados el **31 de octubre de 2026**:

| Trámite | Fuente oficial |
|---|---|
| Obtención del Diploma Académico | [titulos.umsa.bo/tramites](https://titulos.umsa.bo/tramites) → *Requisitos para obtención del Diploma Académico* |
| Título Profesional (ex Provisión Nacional), R-271 v10 | [titulos.umsa.bo/tramites](https://titulos.umsa.bo/tramites) → *Requisitos para Título Profesional* |

- Pregunta lo que cambia los requisitos: **nacionalidad**, **carrera** (Medicina, Odontología, Enfermería, Informática, Derecho) y **excelencia académica**.
- Devuelve requisitos, costos, pasos, entrega y notas **solo** desde la capability `tramites` de `capacidades.py`, siempre con el enlace a la fuente.
- Todo sale de cinco tools: `listar_tramites`, `consultar_tramite`, `revisar_requisitos`, `consultar_dependencias` y `estado_catalogo`.
- Si le dices qué documentos ya tienes, arma la **lista de verificación**: qué tienes, qué te falta y qué falta confirmar.
- Explica que el **Diploma Académico va antes** del Título Profesional (hay que legalizarlo primero).
- Avisa si la ficha del catálogo **no se revisa hace más de 180 días**, y muestra cuándo se revisó y qué cambió en el catálogo.
- Si el trámite no está en el catálogo, lo dice; no inventa requisitos, costos ni plazos.
- Aclara que es un **prototipo independiente**: orienta, no confirma ni realiza trámites.
- Además responde **consultas generales** con la capability `apis`: inflación anual de un país (Banco Mundial) y temperatura actual de La Paz (Open Meteo), siempre citando la fuente.

Prueba estas preguntas:
- «¿Qué necesito para sacar mi diploma académico?»
- «Soy extranjero y quiero el título profesional, ¿qué documentos presento?»
- «Estudié Medicina, ¿qué requisito extra tengo para el título?»
- «¿Cuánto cuesta el título profesional si soy excelencia académica?»
- «Ya tengo mi certificado de biblioteca y las fotos, ¿qué más necesito para el diploma?»
- «¿Puedo sacar el título profesional sin el diploma académico?»
- «¿La información del catálogo está actualizada?»

El alcance completo del proyecto está en **[docs/tramia.md](docs/tramia.md)** (BRD).

### Lo que quedó de la plantilla

La plantilla del curso sigue en el repositorio como material de estudio. `apis` está conectada al agente; `consulta`, `registro` y `documentos` todavía no:

| Trae | Sesión | Dónde |
|---|---|---|
| Tools de lectura con APIs públicas (inflación del Banco Mundial, clima de Open Meteo) | S1 | `capacidades.py` → `apis` |
| Mi contador: gastos en SQLite, una tool que lee y otra que escribe | S1 | `capacidades.py` → `consulta` y `registro` |
| RAG: buscar en PDFs y citar la fuente | S2 | `capacidades.py` → `documentos` |
| El agente y su núcleo async: `responder(mensaje)` | S5 | `asistente.py` |
| El bot de Telegram con lista de permitidos: *polling* en tu equipo y webhook en Render | S5 | `bot.py` |

El asistente **no tiene memoria**: cada mensaje empieza de cero.

Lo que tienes que hacer y cómo se califica está en **[TRABAJO_FINAL.md](TRABAJO_FINAL.md)**.

---

## 0 · Lo que necesitas

| Qué | Para qué | Dónde |
|---|---|---|
| **uv** y **git** | Instalar y ejecutar; subir tu código | Los instalaste en la S0. En Windows, usa **Git Bash** |
| Una cuenta de **GitHub** | Guardar tu código; Render lo lee de ahí | [github.com](https://github.com) |
| Una clave de **DeepSeek** | El modelo | [platform.deepseek.com](https://platform.deepseek.com) (se paga por uso; unos centavos por conversación) |
| *Opcional:* una clave de **Gemini** (gratis) | Para volver a Gemini con `MODO=gemini`, y para los embeddings de la práctica de RAG | [aistudio.google.com/apikey](https://aistudio.google.com/apikey), en un proyecto **sin facturación** |
| **Telegram** | Crear y usar el bot | [telegram.org](https://telegram.org) |
| Una cuenta de **Render** (gratis, sin tarjeta) | Publicar el bot en internet | [render.com](https://render.com): entra con *GitHub* |

## 1 · Tu copia de la plantilla

1. Arriba en esta página, pulsa **Use this template → Create a new repository**.
2. Ponle un nombre, por ejemplo `tramia`. Puede ser **privado**.
3. Clónalo y entra en la carpeta:

```bash
git clone https://github.com/TU-USUARIO/tramia.git
cd tramia
```

## 2 · En tu equipo

```bash
cp .env.example .env     # y escribe tu DEEPSEEK_API_KEY en .env (nunca subas .env)
uv sync                  # instala Python 3.14 y las dependencias en .venv/
uv run asistente.py      # conversa en la terminal; «salir» para terminar
```

Prueba las preguntas de «Qué hace este MVP»: salen del catálogo y citan la fuente oficial.

Para comprobar el código sin gastar cuota del modelo, corre `uv run pytest`.

## 3 · Tu bot de Telegram

**3.1 · Crea el bot**
1. En Telegram, busca **@BotFather** (con la marca azul de verificado) y pulsa *Iniciar*.
2. Escribe `/newbot`.
3. Escribe el **nombre** que verá la gente, por ejemplo «Asistente de Ana».
4. Escribe el **usuario**, que tiene que terminar en `bot`, por ejemplo `asistente_de_ana_bot`.
5. BotFather te da un **token** como `7812345678:AAH…`. Cópialo en `.env`: `TELEGRAM_TOKEN=7812345678:AAH…`

El token es la llave del bot: quien lo tenga lo controla. No lo compartas ni lo subas. Si se filtra, escribe `/revoke` en @BotFather para invalidarlo.

**3.2 · Arráncalo en tu equipo y averigua tu número de chat**

```bash
# En .env: TELEGRAM_POLLING_LOCAL=true (solo para probarlo en tu equipo)
uv run uvicorn api:app --reload
```

Abre tu bot en Telegram (el enlace `t.me/…_bot` que te dio BotFather) y pulsa **Iniciar** o escribe `/start`. Te responde «Tu número de chat es 123456789…».

> **Cuidado:** el polling local elimina el webhook de Render para ese mismo bot. Si ya está desplegado, deja `TELEGRAM_POLLING_LOCAL=false` y pruébalo desde Render. No uses el mismo token en local y Render a la vez.

**3.3 · Autorízate**
1. Detén el bot con Ctrl+C.
2. Pon ese número en `.env`: `TELEGRAM_PERMITIDOS=123456789`. Para varias personas, sepáralas con comas: `TELEGRAM_PERMITIDOS=123456789,987654321`.
   > **No es tu número de teléfono.** Es el número que te dio `/start`: sin `+`, sin código de país y sin espacios.
3. Reinicia `uv run uvicorn api:app --reload` y escríbele (con `TELEGRAM_POLLING_LOCAL=true`).

> **¿Cualquiera puede escribirle a mi bot?** Cualquiera que encuentre su usuario puede *escribirle*: en Telegram no hay bots privados. Pero el bot solo *responde* a los números de `TELEGRAM_PERMITIDOS`. Al resto le contesta «No autorizado» **sin llamar al modelo**, así que no gastan tu cuota. Si la lista está vacía, no le responde a nadie.

En tu equipo, el mismo servidor de la web puede hacer ***polling*** si lo activas expresamente. En Render usa **webhook**: Telegram envía los mensajes al mismo servidor que atiende la web, sin otro proceso ni puerto.

## 4 · Despliegue en Render (paso a paso, a mano)

**4.1 · Sube tu código a GitHub**

```bash
git status               # .env NO debe aparecer en la lista
git add .
git commit -m "Mi asistente"
git push
```

**4.2 · Crea el servicio**
1. Entra a [dashboard.render.com](https://dashboard.render.com) con tu cuenta de GitHub.
2. Pulsa **+ New → Web Service**.
3. En *Source Code*, elige **GitHub**. La primera vez, pulsa *Configure GitHub* (o *Connect GitHub*) y dale acceso a tu repositorio.
4. Elige tu repositorio y completa:

| Campo | Valor |
|---|---|
| **Name** | `tramia`. Será parte de la URL: `https://tramia.onrender.com` (los nombres son únicos: si ya está tomado, agrega un sufijo) |
| **Language** | `Python 3` |
| **Branch** | `main` |
| **Region** | La que quieras, por ejemplo *Virginia (US East)* |
| **Root Directory** | (vacío) |
| **Build Command** | `uv sync --locked --no-dev` |
| **Start Command** | `uv run --no-sync uvicorn api:app --host 0.0.0.0 --port $PORT` |
| **Instance Type** | **Free** |

5. En **Environment Variables**, pulsa *Add Environment Variable* y agrega:

| Key | Value |
|---|---|
| `DEEPSEEK_API_KEY` | Tu clave de DeepSeek |
| `GEMINI_API_KEY_LOCAL` | Solo si vuelves a Gemini o usas el RAG |
| `TELEGRAM_TOKEN` | El token de BotFather |
| `TELEGRAM_PERMITIDOS` | Tu número de chat y el del docente, separados por coma |
| `SESION_SECRETO` | Secreto de sesión (usa **Generate** en Render) |
| `COOKIE_SEGURA` | `true` (Render usa HTTPS) |

6. Pulsa **Deploy Web Service**. La primera vez tarda unos minutos.

**4.3 · Comprueba que funciona**
1. En **Logs** debe aparecer `Webhook en https://tramia.onrender.com/telegram` y luego *Your service is live 🎉*.
2. **Desactiva el polling local** (`TELEGRAM_POLLING_LOCAL=false`) antes de probar Render con el mismo token.
3. Abre la web en la URL del servicio y prueba el bot de Telegram. Ambos funcionan desde el mismo servidor.

En Render, `api.py` registra `/telegram` como **webhook** cuando Render define `RENDER_EXTERNAL_URL`. Antes de aceptar mensajes, compara el encabezado secreto enviado por Telegram; luego `bot.py` rechaza a quien no esté en `TELEGRAM_PERMITIDOS` **antes** de llamar al modelo.

**4.4 · Actualizar**
- Cada `git push` a `main` vuelve a desplegar solo.
- Si cambias una variable en **Environment** y la guardas, también se vuelve a desplegar.

> **Atajo opcional:** en lugar de los pasos 2 a 6 de 4.2, puedes usar **+ New → Blueprint**. Elige tu repositorio y rellena las variables que te pide: Render lee `render.yaml`, que tiene la misma configuración.

### Límites del plan Free

| Límite | Qué significa |
|---|---|
| **Se duerme** tras 15 minutos sin mensajes | El primer mensaje tarda alrededor de un minuto en responder; los siguientes son rápidos |
| **El disco es efímero** | Al dormirse o redesplegar se borra lo escrito en disco. TRAMIA no guarda datos, así que no le afecta; la práctica de gastos sí perdería lo registrado |
| 512 MB de memoria | Alcanza con DeepSeek o Gemini; Ollama no cabe |
| Los `429` son cuota | Mira los *Logs*. La cuota de Gemini gratis es **diaria**; DeepSeek se paga por uso. Espera o cambia de modelo con `MODO` |

## Interfaz web (extra opcional)

TRAMIA también tiene una web con **login, historial y chat**, servida por el mismo `api.py` que recibe Telegram. React vive en `web/`, pero al repositorio solo entra **ya compilado** en `web/dist`: **un solo servicio de Render** alcanza, sin base de datos y sin Node en producción.

```bash
uv run uvicorn api:app --reload      # http://127.0.0.1:8000, sirve web/dist
```

Para cambiar la interfaz, compílala en tu equipo y versiona el nuevo `web/dist`:

```bash
cd web && pnpm install && pnpm build && cd ..
```

La web usa sesiones sin base de datos. Las conversaciones se guardan en memoria: al reiniciar el servicio empiezan de cero.

**No hace falta para el trabajo final.** Las instrucciones completas, incluido el despliegue, están en [WEB.md](WEB.md).

## 5 · Hazlo tuyo

- **Instrucciones** (`asistente.py`): para quién es, qué hace y qué no.
- **Datos del catálogo** (`capacidades.py` → `TRAMITES`): los trámites, requisitos, costos y fuentes. Cada ficha lleva `revisado`, `estado` e `historial`; cada requisito, una lista `claves` con las palabras que usa la gente para nombrarlo (así funciona la lista de verificación). Para agregar un trámite: copia su ficha, añade su clave al `Literal` `Tramite` y, si depende de otro, decláralo en `DEPENDENCIAS`.
- **Tools y capabilities** (`capacidades.py`): agrega las tuyas y conéctalas en `asistente.py`, en `capabilities=[...]`. Ideas:
  - otra API pública;
  - búsqueda web (S2);
  - un servidor MCP (S3);
  - un flujo con un grafo (S4).
- **Dependencias:** `uv add nombre-paquete`, nunca a mano. Luego haz commit de `pyproject.toml` y `uv.lock`.

> **Mantenimiento del catálogo:** cada gestión, compara las fichas con los instructivos publicados, actualiza `revisado` y agrega una línea a `historial`. Pasados `VIGENCIA_DIAS` (180) sin revisión, el bot avisa que la ficha está *por verificar* y pide confirmar en el canal oficial: no la presenta como vigente.

> **Extra opcional:** si además quieres usar tu asistente como API HTTP, sigue [API.md](API.md). No hace falta para el trabajo final.

## 6 · Pide ayuda a una IA

Este repositorio trae un **skill** con lo que vimos en el curso: reglas, recetas con el código de clase y una tabla de errores reales. Está en [`.agents/skills/asistente-pydantic-ai/`](.agents/skills/asistente-pydantic-ai/SKILL.md).

| Herramienta | Cómo lo usa |
|---|---|
| **Claude Code** | Solo: lee `CLAUDE.md` y el skill. Pídele, por ejemplo: «agrega una capability con la API de tipos de cambio» |
| **Codex**, **Cursor**, **GitHub Copilot**, **Gemini CLI** | Leen `AGENTS.md`, que les dice dónde está el skill |
| **ChatGPT**, **Claude.ai**, **Gemini** (en la web) | Adjunta `SKILL.md` y la referencia que necesites (por ejemplo, `referencias/errores.md`), y pega tu código y el error completo |

La IA te ayuda, pero el código es tuyo: entiende cada cambio antes de aceptarlo, y nunca le pegues tus claves ni tokens.

## 7 · Problemas frecuentes

| Ves | Qué hacer |
|---|---|
| `ValidationError … gemini_api_key_local` o `Falta TELEGRAM_TOKEN` | Ponlas en `.env` (equipo) o en *Environment* (Render) |
| El bot responde «No autorizado. Tu chat es N» | Agrega N a `TELEGRAM_PERMITIDOS` y reinicia el bot (en Render, guarda la variable) |
| El bot responde «Algo falló…» | Mira la terminal o los *Logs* de Render: ahí está el error real (un `429` es cuota) |
| El bot de Render dejó de responder **después de probar en tu equipo** | Al arrancar, el *polling* local borra el webhook. En Render: **Manual Deploy → Restart service** |
| `Conflict: terminated by other getUpdates request` | Hay dos bots en *polling* con el mismo token: deja uno solo |
| El build de Render falla por `uv.lock` | Cambiaste dependencias sin `uv lock`: corre `uv lock`, commit y push |
| Más errores (async, MCP, grafos) | [`referencias/errores.md`](.agents/skills/asistente-pydantic-ai/referencias/errores.md) |

## Archivos

```
├── config.py           la configuración (.env o Render) y el modelo
├── capacidades.py      tramites (TRAMIA) + apis, consulta, registro y documentos (práctica)
├── asistente.py        el agente y responder(mensaje)
├── bot.py              handlers de Telegram: /start y lista de permitidos
├── api.py              servidor único: web, API y webhook de Telegram
├── sesion.py           login sin base de datos: hash de contraseña y cookie firmada
├── conversaciones.py   las conversaciones de la web, en memoria
├── web/                la interfaz React: al repo solo entra web/dist compilado
├── datos/              gastos.csv y documentos/*.pdf (práctica del curso)
├── tests/              pruebas sin modelo real
├── pyproject.toml      dependencias (uv.lock las fija)
├── .python-version     Python 3.14 (lo leen uv y Render)
├── .env.example        las variables, sin valores
├── render.yaml         atajo para Render (Blueprint)
├── TRABAJO_FINAL.md    qué se entrega y cómo se califica
├── API.md              extra opcional: el asistente como API
├── WEB.md              extra opcional: la interfaz web con login
├── AGENTS.md, CLAUDE.md  instrucciones para asistentes de IA
└── .agents/skills/     el skill del curso
```

---

Autor: **Alex Ojeda Copa**. Código bajo licencia [MIT](LICENSE).
