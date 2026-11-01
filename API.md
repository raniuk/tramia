# Extra opcional: tu asistente como API

**No hace falta para el trabajo final.** Lo principal es el bot de Telegram del [README](README.md). La API permite que, además, otros programas usen tu asistente: un script, otra app o n8n.

La API es el archivo `api.py`. Recibe un mensaje por HTTP y devuelve la respuesta del **mismo** `responder(mensaje)` que usa el bot. Si cambias una tool en `capacidades.py`, la toman los dos.

```
POST /chat   Authorization: Bearer <tu token>   {"mensaje": "¿Cuánto gasté en transporte?"}
         →   {"texto": "En transporte gastaste 67 bolivianos en total."}
```

## 1 · Crea tu token

Igual que el bot solo responde a los números de `TELEGRAM_PERMITIDOS`, la API solo responde a quien mande un token de `API_TOKENS`. Sin token, contesta `401` **sin llamar al modelo**, así que nadie gasta tu cuota. Si la lista está vacía, no entra nadie.

1. Genera un token:
   ```bash
   uv run python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```
2. Ponlo en `.env`:
   ```
   API_TOKENS=el-token-que-salió
   ```
   Para varias personas, genera un token para cada una y sepáralos con comas. Si uno se filtra, borras solo ese.

> **No reutilices el token de Telegram.** Ese token es la llave del bot: quien lo tenga puede leer sus mensajes y hacerse pasar por él. Cada cosa lleva su propia llave.

## 2 · Pruébala en tu equipo

```bash
uv run uvicorn api:app --reload
```

- Abre **http://127.0.0.1:8000/docs**: FastAPI arma una página para probarla. Pulsa **Authorize**, pega tu token y luego, en `POST /chat`, *Try it out*.
- O desde la terminal:
  ```bash
  curl -X POST http://127.0.0.1:8000/chat \
    -H "Authorization: Bearer el-token-que-salió" \
    -H "Content-Type: application/json" \
    -d '{"mensaje": "¿Cuánto gasté en transporte?"}'
  ```

| Respuesta | Qué significa |
|---|---|
| `200` y `{"texto": …}` | Funciona |
| `401 Token inválido` | Falta el token, está mal o `API_TOKENS` está vacío |
| `422` | El pedido no cumple el contrato: falta `mensaje`, está vacío o pasa de 2000 caracteres |
| `500` | Falló el modelo o una tool: el error está en la terminal (un `429` es cuota) |

## 3 · Publícala en Render

La API, la web y el webhook del bot ya comparten **un solo servicio**. No crees un segundo servicio para esta API.

1. Sigue [WEB.md, sección 4](WEB.md#4--publícala-en-render) para desplegar el servidor único.
2. Si también quieres habilitar `/chat` para otros programas, agrega `API_TOKENS` en **Environment** con un token generado como en el paso 1. Sin tokens, `/chat` responde 401, pero la web y Telegram funcionan igual.

Prueba `POST /chat` como en el paso 2, con `https://tramia.onrender.com` en lugar de `http://127.0.0.1:8000`. Cada despliegue actualiza el mismo servicio para la web, Telegram y la API.

## Cuidado

- El token sirve cuando la API la llama **un programa**. Si haces una página web que llama a la API **desde el navegador**, cualquiera puede ver el token en las herramientas de desarrollo. Para eso hace falta un login o un servidor intermedio.
- Nunca escribas un token en el código ni lo subas a GitHub: va en `.env` y en *Environment*.
- `uv run pytest` incluye dos pruebas de la API: sin token válido no se llama al modelo, y con token responde.
