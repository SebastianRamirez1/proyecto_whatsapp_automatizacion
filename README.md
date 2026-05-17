# Sistema de Automatización de Pedidos por WhatsApp

Backend para automatizar la recepción y gestión de pedidos enviados por WhatsApp Business.  
Stack: **Python · FastAPI · PostgreSQL · OpenAI · Meta Cloud API · Docker**

---

## Arquitectura

```
Cliente WhatsApp
      │
      ▼
[Meta Cloud API]
      │  webhook POST
      ▼
[FastAPI — Webhook Receiver]
      │
      ├──► [Interpretador IA]   → extrae intención + campos del pedido
      ├──► [Gestor de Pedidos]  → escribe en PostgreSQL
      └──► [Notificador WA]     → confirma al cliente automáticamente

[API REST Admin]
      └──► CRUD pedidos / estados / reportes (JWT protegido)
```

## Módulos

| Módulo | Descripción |
|--------|-------------|
| Webhook receiver | Recibe eventos de WhatsApp Business API, valida firma Meta |
| Motor IA | Clasifica intención y extrae campos con GPT-4o-mini |
| Gestor de pedidos | CRUD en PostgreSQL, máquina de estados |
| Notificador | Envía confirmaciones y actualizaciones de estado al cliente |
| API Admin | Endpoints REST con JWT para gestión del negocio |

## Requisitos

- Python 3.11+
- Docker & Docker Compose
- Cuenta Meta Developers (WhatsApp Business API)
- API Key de OpenAI

## Inicio rápido

```bash
# 1. Clonar repositorio
git clone https://github.com/SebastianRamirez1/proyecto_whatsapp_automatizacion.git
cd proyecto_whatsapp_automatizacion

# 2. Copiar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# 3. Levantar con Docker
docker compose up --build

# 4. Aplicar migraciones
docker compose exec api alembic upgrade head
```

La API queda disponible en `http://localhost:8000`  
Documentación Swagger: `http://localhost:8000/docs`

## Estados de un pedido

```
recibido → confirmado → en_preparacion → despachado → entregado
                                                    ↘ cancelado
```

## Desarrollo local (sin Docker)

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

## Tests

```bash
pytest -v --cov=app tests/
```

## Deploy

Configurado para Railway / Render. El `Dockerfile` y `docker-compose.yml` funcionan en cualquier VPS.

---

Desarrollado por **Sebastián Ramírez** — ITM Medellín
