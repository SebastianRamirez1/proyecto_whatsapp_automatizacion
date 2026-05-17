import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_db
from app.models.client import Client
from app.models.order import Order, OrderStatus
from app.schemas.order import OrderOut, OrderStatusUpdate
from app.services.orders import get_status_notification_message, transition_order_status
from app.services.whatsapp import send_text_message

logger = logging.getLogger(__name__)
router = APIRouter()


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


@router.get("/orders", response_model=list[OrderOut])
def list_orders(
    order_status: OrderStatus | None = Query(default=None, alias="status"),
    phone: str | None = Query(default=None, description="Filtrar por teléfono del cliente"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List orders with optional filters by status and client phone."""
    query = db.query(Order).options(joinedload(Order.client), joinedload(Order.items))

    if order_status:
        query = query.filter(Order.status == order_status)

    if phone:
        query = query.join(Client).filter(Client.phone == phone)

    return query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()


@router.get("/orders/{order_id}", response_model=OrderOut)
def get_order(order_id: int, db: Session = Depends(get_db)):
    """Get a single order by ID with client and items."""
    return _get_order_or_404(order_id, db)


@router.patch("/orders/{order_id}/status", response_model=OrderOut)
async def update_order_status(
    order_id: int,
    body: OrderStatusUpdate,
    notify: bool = Query(default=True, description="Enviar notificación WhatsApp al cliente"),
    db: Session = Depends(get_db),
):
    """
    Transition an order to a new status.
    Validates the state machine and optionally sends a WhatsApp notification.
    """
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
                logger.error("WhatsApp notification failed | order=%d | error=%s", order.id, exc)

    return order


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_order(order_id: int, db: Session = Depends(get_db)):
    """Cancel an order (shortcut to PATCH status=cancelado)."""
    order = _get_order_or_404(order_id, db)
    try:
        transition_order_status(db, order, OrderStatus.cancelado)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))


@router.get("/orders/summary/stats")
def get_orders_stats(db: Session = Depends(get_db)):
    """Returns order counts grouped by status — useful for a dashboard."""
    counts = {}
    for s in OrderStatus:
        counts[s.value] = db.query(Order).filter(Order.status == s).count()
    total = sum(counts.values())
    return {"total": total, "by_status": counts}
