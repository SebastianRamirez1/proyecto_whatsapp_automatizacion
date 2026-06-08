# MCP Server — Pedidos WhatsApp

Servidor [MCP (Model Context Protocol)](https://modelcontextprotocol.io) que expone
la API de pedidos como herramientas para Claude Desktop, Cursor, o cualquier cliente
compatible con MCP.

Una vez conectado podés preguntarle a Claude cosas como:
- *"¿Cuántos pedidos llegaron hoy?"*
- *"Mostrá todos los pedidos que están en preparación"*
- *"Confirmá el pedido 42 y notificá al cliente"*
- *"¿Qué pedidos están pendientes de entrega?"*

---

## Herramientas disponibles

| Tool | Descripción |
|------|-------------|
| `listar_pedidos` | Lista pedidos con filtros opcionales por estado y teléfono |
| `obtener_pedido` | Detalle completo de un pedido por ID |
| `estadisticas_pedidos` | Conteo total y por estado |
| `actualizar_estado` | Cambia el estado + envía WhatsApp automático al cliente |
| `pedidos_pendientes` | Todos los pedidos que necesitan atención (no finalizados) |

---

## Instalación

### 1. Requisitos previos
- Python 3.11+
- Backend corriendo (Railway o local)

### 2. Instalar dependencias

```bash
# Desde la raíz del repo
pip install -r mcp_server/requirements.txt
```

O con `uv` (recomendado):
```bash
uv pip install -r mcp_server/requirements.txt
```

### 3. Configurar credenciales

```bash
cp mcp_server/.env.example mcp_server/.env
# Editar mcp_server/.env con tu URL y credenciales
```

### 4. Probar que funciona

```bash
python mcp_server/server.py
```

Si no hay errores de importación, el servidor está listo.

---

## Conectar a Claude Desktop

Abrí el archivo de configuración de Claude Desktop:

- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

Agregá esta entrada dentro de `"mcpServers"`:

```json
{
  "mcpServers": {
    "pedidos-whatsapp": {
      "command": "python",
      "args": ["mcp_server/server.py"],
      "cwd": "/ruta/absoluta/al/proyecto_whatsapp_automatico",
      "env": {
        "API_URL": "https://web-production-42788.up.railway.app",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "tu_contraseña"
      }
    }
  }
}
```

> **Reemplazá `/ruta/absoluta/al/proyecto_whatsapp_automatico`** con la ruta real en tu máquina.
> En Windows usá barras invertidas dobles: `"C:\\Users\\SEBASTIAN\\Desktop\\proyecto_whatsapp_automatico"`

Reiniciá Claude Desktop. Deberías ver el servidor "pedidos-whatsapp" conectado en la barra inferior.

---

## Conectar a Cursor

En Cursor, abrí `Cursor Settings > MCP` y agregá un servidor:

```json
{
  "name": "pedidos-whatsapp",
  "command": "python mcp_server/server.py",
  "cwd": "/ruta/al/proyecto",
  "env": {
    "API_URL": "https://web-production-42788.up.railway.app",
    "ADMIN_USERNAME": "admin",
    "ADMIN_PASSWORD": "tu_contraseña"
  }
}
```

---

## Ejemplos de uso en Claude Desktop

Una vez conectado, podés escribir en lenguaje natural:

```
Mostrame los pedidos de hoy que están recibidos pero aún no confirmados
```

```
Confirmá el pedido 15 y avisale al cliente
```

```
¿Cuántos pedidos se entregaron esta semana?
```

```
Hay algún pedido que lleva mucho tiempo en preparación?
```

---

## Arquitectura

```
Claude Desktop / Cursor
        │  MCP Protocol (stdio)
        ▼
mcp_server/server.py   ← FastMCP + 5 tools
        │  HTTP + JWT Bearer
        ▼
FastAPI en Railway     ← /api/v1/orders/*
        │  SQLAlchemy ORM
        ▼
PostgreSQL (Railway)
```

El servidor MCP:
1. Lee credenciales del entorno
2. Hace login automático en el backend al recibir la primera tool call
3. Cachea el JWT y lo renueva automáticamente si expira (401)
4. Traduce cada tool call en una o más llamadas HTTP al backend

---

## Variables de entorno

| Variable | Descripción | Default |
|----------|-------------|---------|
| `API_URL` | URL base del backend FastAPI | `https://web-production-42788.up.railway.app` |
| `ADMIN_USERNAME` | Usuario administrador | — |
| `ADMIN_PASSWORD` | Contraseña del admin | — |
