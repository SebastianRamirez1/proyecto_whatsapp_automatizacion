# MCP Server — Pedidos WhatsApp

Servidor [MCP (Model Context Protocol)](https://modelcontextprotocol.io) que expone
la API de pedidos como herramientas conversacionales para Claude Desktop, Cursor,
o cualquier cliente compatible con MCP.

Una vez conectado podés preguntarle a Claude:
- *"¿Cuántos pedidos llegaron hoy?"*
- *"Confirmá el pedido 42 y notificá al cliente"*
- *"Mostrá los pedidos en preparación"*
- *"¿Hay pedidos sin confirmar hace más de una hora?"*

---

## Herramientas disponibles

| Tool | Descripción |
|------|-------------|
| `listar_pedidos` | Lista pedidos con filtros opcionales de estado y teléfono |
| `obtener_pedido` | Detalle completo de un pedido por ID |
| `estadisticas_pedidos` | Conteo total y por estado |
| `actualizar_estado` | Cambia estado + WhatsApp automático al cliente |
| `pedidos_pendientes` | Todos los pedidos no finalizados agrupados por estado |

---

## Modos de uso

### Modo A — Local con Claude Desktop (stdio)
El proceso MCP corre en tu PC, Claude Desktop se comunica por stdin/stdout.
Sin servidor, sin costos, ideal para uso personal.

### Modo B — Remoto en Railway (SSE)
El MCP server corre en Railway como servicio HTTP. Cualquier Claude Desktop
o Cursor puede conectarse desde cualquier dispositivo usando solo la URL.

---

## Instalación local (Modo A)

### 1. Requisitos
- Python 3.11+
- Backend corriendo (Railway o local)

### 2. Instalar dependencias

```bash
# Opción 1 — desde el repo
pip install -r mcp_server/requirements.txt

# Opción 2 — uvx (instala y ejecuta sin virtualenv)
uvx --from git+https://github.com/SebastianRamirez1/proyecto_whatsapp_automatizacion.git pedidos-whatsapp-mcp
```

### 3. Credenciales

```bash
cp mcp_server/.env.example mcp_server/.env
# Editar mcp_server/.env con tu contraseña
```

### 4. Agregar a Claude Desktop

Abrí el archivo de configuración:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "pedidos-whatsapp": {
      "command": "python",
      "args": ["mcp_server/server.py"],
      "cwd": "/ruta/absoluta/al/proyecto",
      "env": {
        "API_URL": "https://web-production-42788.up.railway.app",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "tu_contraseña"
      }
    }
  }
}
```

> **Windows:** usar `"C:\\Users\\SEBASTIAN\\Desktop\\proyecto_whatsapp_automatico"` como `cwd`.

Reiniciá Claude Desktop. El servidor aparece conectado en la barra inferior.

---

## Deploy en Railway (Modo B — remoto)

### 1. Crear un nuevo servicio en Railway

En tu proyecto Railway:
1. **New Service → GitHub Repo** → seleccionar el mismo repo
2. En **Settings → General**:
   - **Root Directory:** *(vacío — usa la raíz del repo)*
   - **Start Command:** `python mcp_server/server.py`

### 2. Variables de entorno en Railway

| Variable | Valor |
|----------|-------|
| `API_URL` | `https://web-production-42788.up.railway.app` |
| `ADMIN_USERNAME` | `admin` |
| `ADMIN_PASSWORD` | tu contraseña |
| `MCP_SECRET` | una cadena aleatoria segura (ej: `openssl rand -hex 32`) |

> Railway inyecta `PORT` automáticamente — no hace falta configurarlo.

### 3. Conectar desde Claude Desktop (remoto)

Una vez deployed, Railway te da una URL tipo `https://tu-mcp-server.railway.app`.

```json
{
  "mcpServers": {
    "pedidos-whatsapp": {
      "url": "https://tu-mcp-server.railway.app/sse",
      "headers": {
        "Authorization": "Bearer tu_MCP_SECRET_aqui"
      }
    }
  }
}
```

Sin importar dónde estés o qué dispositivo uses, tenés acceso al servidor.

---

## Instalar con `uvx` (Opción B alternativa — sin clonar el repo)

`uvx` instala el paquete en un entorno temporal y lo ejecuta directamente:

```bash
# Instalar y ejecutar desde GitHub (sin clonar)
uvx --from git+https://github.com/SebastianRamirez1/proyecto_whatsapp_automatizacion.git \
    pedidos-whatsapp-mcp
```

Con variables de entorno:
```bash
API_URL=https://... ADMIN_USERNAME=admin ADMIN_PASSWORD=pass \
uvx --from git+https://github.com/SebastianRamirez1/proyecto_whatsapp_automatizacion.git \
    pedidos-whatsapp-mcp
```

En `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "pedidos-whatsapp": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/SebastianRamirez1/proyecto_whatsapp_automatizacion.git",
        "pedidos-whatsapp-mcp"
      ],
      "env": {
        "API_URL": "https://web-production-42788.up.railway.app",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "tu_contraseña"
      }
    }
  }
}
```

No hace falta clonar el repo ni instalar dependencias manualmente.

---

## Arquitectura

```
┌─────────────────────────┐
│  Claude Desktop / Cursor │
│  (cualquier dispositivo) │
└────────────┬────────────┘
             │
    MCP Protocol
    stdio (local) o SSE (remoto)
             │
┌────────────▼────────────┐
│   mcp_server/server.py   │
│   FastMCP + 5 tools      │
│   Auto-detect transport  │
│   JWT cache + refresh    │
└────────────┬────────────┘
             │
    HTTP + Bearer JWT
             │
┌────────────▼────────────┐
│  FastAPI en Railway      │
│  /api/v1/orders/*        │
└────────────┬────────────┘
             │
┌────────────▼────────────┐
│  PostgreSQL (Railway)    │
└─────────────────────────┘
```

### Flujo de autenticación
1. Primera tool call → login automático con `ADMIN_USERNAME` / `ADMIN_PASSWORD`
2. JWT cacheado en memoria → reutilizado en llamadas siguientes
3. Si expira (401) → re-login automático, transparente para el usuario
4. En modo SSE: `MCP_SECRET` guard valida el Bearer token del cliente MCP

---

## Variables de entorno

| Variable | Descripción | Requerida |
|----------|-------------|-----------|
| `API_URL` | URL base del backend FastAPI | Sí |
| `ADMIN_USERNAME` | Usuario administrador | Sí |
| `ADMIN_PASSWORD` | Contraseña admin | Sí |
| `MCP_SECRET` | Token para proteger el endpoint SSE | Solo en modo remoto |
| `PORT` | Puerto HTTP (Railway lo inyecta automáticamente) | Auto |
