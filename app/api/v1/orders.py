import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.core.security import get_current_user
from app.db.session import get_db
from app.models.client import Client
from app.models.order import Order, OrderStatus
from app.schemas.order import OrderOut, OrderStatusUpdate
from app.services.orders import get_status_notification_message, transition_order_status
from app.services.whatsapp import send_text_message

logger = logging.getLogger(__name__)
router = APIRouter()

_AUTH = Depends(get_current_user)


def _get_order_or_404(order_id: int, db: Session) -> Order:
    order = (
        db.query(Order)
        .options(joinedload(Order.client), joinedload(Order.items))
        .filter(Order.id == order_id)
        .first()
    )
    if not order:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Order not found")
    return order


@router.get(
    "/orders",
    response_model=list[OrderOut],
    summary="Listar pedidos",
    description="Devuelve pedidos ordenados por fecha descendente. Filtra por estado y/o teléfono del cliente.",
    dependencies=[_AUTH],
)
def list_orders(
    order_status: OrderStatus | None = Query(default=None, alias="status", description="Filtrar por estado"),
    phone: str | None = Query(default=None, description="Teléfono del cliente (ej. 573001234567)"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    query = db.query(Order).options(joinedload(Order.client), joinedload(Order.items))
    if order_status:
        query = query.filter(Order.status == order_status)
    if phone:
        query = query.join(Client).filter(Client.phone == phone)
    return query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()


@router.get(
    "/orders/summary/stats",
    summary="Estadísticas de pedidos",
    description="Conteo de pedidos agrupado por estado. Útil para el dashboard del negocio.",
    dependencies=[_AUTH],
)
def get_orders_stats(db: Session = Depends(get_db)):
    counts = {s.value: db.query(Order).filter(Order.status == s).count() for s in OrderStatus}
    return {"total": sum(counts.values()), "by_status": counts}


@router.get(
    "/orders/{order_id}",
    response_model=OrderOut,
    summary="Detalle de un pedido",
    dependencies=[_AUTH],
)
def get_order(order_id: int, db: Session = Depends(get_db)):
    return _get_order_or_404(order_id, db)


@router.patch(
    "/orders/{order_id}/status",
    response_model=OrderOut,
    summary="Cambiar estado del pedido",
    description=(
        "Avanza el pedido en la máquina de estados. "
        "Si `notify=true` (default) envía un mensaje WhatsApp automático al cliente."
    ),
    dependencies=[_AUTH],
)
async def update_order_status(
    order_id: int,
    body: OrderStatusUpdate,
    notify: bool = Query(default=True, description="Notificar al cliente por WhatsApp"),
    db: Session = Depends(get_db),
):
    order = _get_order_or_404(order_id, db)
    try:
        order = transition_order_status(db, order, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))

    if notify and order.client:
        message = get_status_notification_message(order)
        if message:
            try:
                await send_text_message(to=order.client.phone, body=message)
            except Exception as exc:
                logger.error("WA notification failed | order=%d | error=%s", order.id, exc)

    return order


@router.delete(
    "/orders/{order_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancelar pedido",
    description="Cancela el pedido si su estado lo permite. Equivale a PATCH status=cancelado.",
    dependencies=[_AUTH],
)
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    order = _get_order_or_404(order_id, db)
    try:
        transition_order_status(db, order, OrderStatus.cancelado)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
