import logging

from sqlalchemy.orm import Session

from app.models.client import Client
from app.models.order import Order, OrderStatus
from app.models.order_item import OrderItem
from app.schemas.interpretation import InterpretationResult, MessageIntent

logger = logging.getLogger(__name__)

# Transiciones válidas de estado
_VALID_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.recibido: {OrderStatus.confirmado, OrderStatus.cancelado},
    OrderStatus.confirmado: {OrderStatus.en_preparacion, OrderStatus.cancelado},
    OrderStatus.en_preparacion: {OrderStatus.despachado, OrderStatus.cancelado},
    OrderStatus.despachado: {OrderStatus.entregado},
    OrderStatus.entregado: set(),
    OrderStatus.cancelado: set(),
}

# Mensaje que se envía al cliente en cada transición
STATUS_MESSAGES: dict[OrderStatus, str] = {
    OrderStatus.confirmado: (
        "✅ Tu pedido #{order_id} fue *confirmado*. "
        "Pronto lo ponemos en preparación."
    ),
    OrderStatus.en_preparacion: (
        "👨‍🍳 Tu pedido #{order_id} está *en preparación*. "
        "Te avisamos cuando salga para entrega."
    ),
    OrderStatus.despachado: (
        "🚚 Tu pedido #{order_id} ya va *en camino*. "
        "Nuestro repartidor está en ruta."
    ),
    OrderStatus.entregado: (
        "🎉 Tu pedido #{order_id} fue *entregado*. "
        "¡Gracias por tu compra! ¿En qué más te podemos ayudar?"
    ),
    OrderStatus.cancelado: (
        "❌ Tu pedido #{order_id} fue *cancelado*. "
        "Si fue un error, escríbenos y lo gestionamos."
    ),
}


def get_or_create_client(db: Session, phone: str, name: str | None = None) -> Client:
    client = db.query(Client).filter(Client.phone == phone).first()
    if not client:
        client = Client(phone=phone, name=name)
        db.add(client)
        db.flush()
        logger.info("New client created | phone=%s", phone)
    return client


def create_order_from_interpretation(
    db: Session,
    client: Client,
    result: InterpretationResult,
    raw_message: str,
    wa_message_id: str | None = None,
) -> Order:
    order = Order(
        client_id=client.id,
        status=OrderStatus.recibido,
        raw_message=raw_message,
        delivery_address=result.direccion_entrega,
        notes=result.observaciones,
        wa_message_id=wa_message_id,
    )
    db.add(order)
    db.flush()

    for extracted in result.items:
        item = OrderItem(
            order_id=order.id,
            product_name=extracted.producto,
            quantity=extracted.cantidad,
            unit=extracted.unidad,
        )
        db.add(item)

    db.commit()
    db.refresh(order)
    logger.info("Order created | id=%d | client=%s | items=%d", order.id, client.phone, len(order.items))
    return order


def transition_order_status(db: Session, order: Order, new_status: OrderStatus) -> Order:
    allowed = _VALID_TRANSITIONS.get(order.status, set())
    if new_status not in allowed:
        raise ValueError(
            f"Transición inválida: {order.status} → {new_status}. "
            f"Permitidas: {[s.value for s in allowed]}"
        )
    order.status = new_status
    db.commit()
    db.refresh(order)
    logger.info("Order status updated | id=%d | new_status=%s", order.id, new_status)
    return order


def get_status_notification_message(order: Order) -> str | None:
    template = STATUS_MESSAGES.get(order.status)
    if not template:
        return None
    return template.format(order_id=order.id)
