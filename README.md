# Sistema de Automatización de Pedidos por WhatsApp

> Backend que elimina la gestión manual de pedidos recibidos por WhatsApp.  
> El cliente escribe, el sistema entiende, registra y confirma — sin intervención humana.

**Stack:** Python 3.11 · FastAPI · PostgreSQL · OpenAI GPT-4o-mini · Meta Cloud API · Docker  
**Deploy:** Railway · Swagger en `/docs`

---

## El problema que resuelve

Negocios de toda escala (distribuidoras, restaurantes, textiles) reciben pedidos por WhatsApp de forma manual. Alguien los anota, otro los transcribe, otro los confirma. Hay errores y caos.

Este sistema elimina esa cadena:

```
Cliente WhatsApp → IA interpreta → PostgreSQL guarda → Bot confirma con N° de pedido
Admin cambia estado → Cliente recibe notificación automática
```

---

## Arquitectura

```
Cliente WhatsApp
      │
      ▼
[Meta Cloud API]
      │  POST /api/v1/webhook
      ▼
[FastAPI — Webhook Receiver]          ← valida firma HMAC-SHA256 de Meta
      │
      ├──► [Motor IA — GPT-4o-mini]   ← clasifica intención + extrae campos
      │         │
      │         ▼
      ├──► [Gestor de Pedidos]         ← escribe Client + Order + OrderItem en PostgreSQL
      │
      └──► [Notificador WhatsApp]      ← confirma al cliente con #ID de pedido

[API REST Admin — JWT protegida]
      ├── GET  /orders              ← lista con filtros
      ├── GET  /orders/{id}         ← detalle
      ├── PATCH /orders/{id}/status ← avanza estado + notifica al cliente
      ├── DELETE /orders/{id}       ← cancela
      └── GET  /orders/summary/stats ← dashboard
```

---

## Intenciones que entiende el bot

| Mensaje del cliente | Intención detectada | Respuesta automática |
|---------------------|--------------------|-----------------------|
| "3 cubetas AA a Calle 50" | `nuevo_pedido` | Confirmación con #ID |
| "¿cómo va mi pedido?" | `consulta_estado` | Instrucciones para consultar |
| "cancela mi pedido" | `cancelacion` | Confirmación de gestión |
| "hola" | `saludo` | Bienvenida + instrucciones |
| Mensaje confuso | `ambiguo` | Pregunta de aclaración específica |

---

## Máquina de estados

```
recibido ──► confirmado ──► en_preparacion ──► despachado ──► entregado
    │              │                │
    └──────────────┴────────────── cancelado
```

Cada transición dispara un mensaje WhatsApp automático al cliente.  
Transiciones inválidas son rechazadas con `400 Bad Request`.

---

## Inicio rápido (Docker)

```bash
# 1. Clonar
git clone https://github.com/SebastianRamirez1/proyecto_whatsapp_automatizacion.git
cd proyecto_whatsapp_automatizacion

# 2. Variables de entorno
cp .env.example .env
# Editar .env con tus credenciales de Meta, OpenAI y generar SECRET_KEY

# 3. Levantar
docker compose up --build

# 4. Aplicar migración
docker compose exec api alembic upgrade head
```

| Servicio | URL |
|----------|-----|
| API | http://localhost:8000 |
| Swagger | http://localhost:8000/docs |
| ReDoc | http://localhost:8000/redoc |
| Health | http://localhost:8000/health |

---

## Desarrollo local (sin Docker)

```bash
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

pip install -r requirements.txt

# PostgreSQL local corriendo, luego:
alembic upgrade head
uvicorn app.main:app --reload
```

---

## Variables de entorno requeridas

| Variable | Descripción |
|----------|-------------|
| `DATABASE_URL` | URL de PostgreSQL |
| `WHATSAPP_VERIFY_TOKEN` | Token de verificación del webhook Meta |
| `WHATSAPP_ACCESS_TOKEN` | Token de acceso de la app Meta |
| `WHATSAPP_PHONE_NUMBER_ID` | ID del número de WhatsApp Business |
| `META_APP_SECRET` | Secret para validar firma HMAC de webhooks |
| `OPENAI_API_KEY` | API key de OpenAI |
| `SECRET_KEY` | Clave para firmar JWT (mínimo 32 chars) |
| `ADMIN_USERNAME` | Usuario del administrador |
| `ADMIN_PASSWORD_HASH` | Hash bcrypt de la contraseña admin |

Generar `SECRET_KEY`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Generar `ADMIN_PASSWORD_HASH`:
```bash
python -c "from passlib.context import CryptContext; print(CryptContext(['bcrypt']).hash('tu_password'))"
```

---

## API Admin — Uso básico

```bash
# 1. Obtener token
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "tu_password"}'

# 2. Listar pedidos recibidos
curl http://localhost:8000/api/v1/orders?status=recibido \
  -H "Authorization: Bearer <token>"

# 3. Confirmar un pedido (notifica automáticamente al cliente por WA)
curl -X PATCH http://localhost:8000/api/v1/orders/42/status \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"status": "confirmado"}'

# 4. Ver estadísticas
curl http://localhost:8000/api/v1/orders/summary/stats \
  -H "Authorization: Bearer <token>"
```

---

## Deploy en Railway

1. Crear proyecto en [Railway](https://railway.app) → **Deploy from GitHub**
2. Agregar plugin **PostgreSQL** — Railway inyecta `DATABASE_URL` automáticamente
3. Configurar las variables de entorno en el panel de Railway
4. El `railway.json` incluido aplica la migración y levanta el servidor automáticamente

---

## Tests

```bash
pytest -v --cov=app tests/
```

Cobertura de:
- Verificación y recepción del webhook (firma HMAC)
- Motor de interpretación IA (con mocks de OpenAI)
- Servicio de pedidos: creación, máquina de estados, notificaciones
- Autenticación JWT: login, endpoints protegidos, tokens inválidos

---

## Estructura del proyecto

```
app/
├── api/v1/
│   ├── auth.py        # POST /auth/login → JWT
│   ├── webhook.py     # GET+POST /webhook (Meta Cloud API)
│   └── orders.py      # CRUD admin de pedidos
├── core/
│   ├── config.py      # Settings con pydantic-settings
│   └── security.py    # HMAC, JWT, bcrypt
├── db/session.py      # SQLAlchemy engine + get_db
├── models/            # Client, Order, OrderItem
├── schemas/           # Pydantic: webhook, interpretación, orden, auth
└── services/
    ├── interpretation.py  # GPT-4o-mini → InterpretationResult
    ├── orders.py          # Lógica de negocio + máquina de estados
    └── whatsapp.py        # Envío de mensajes via Meta API
alembic/versions/
└── 0001_initial_schema.py
tests/
├── test_webhook.py
├── test_interpretation.py
├── test_orders.py
└── test_auth.py
```

---

**Sebastián Ramírez** · ITM Medellín · sebastianacevedo123.sra@gmail.com
