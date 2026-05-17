from datetime import datetime

from pydantic import BaseModel

from app.models.order import OrderStatus


class OrderItemOut(BaseModel):
    id: int
    product_name: str
    quantity: int
    unit: str | None
    unit_price: float | None

    class Config:
        from_attributes = True


class ClientOut(BaseModel):
    id: int
    phone: str
    name: str | None

    class Config:
        from_attributes = True


class OrderOut(BaseModel):
    id: int
    client_id: int
    client: ClientOut | None = None
    status: OrderStatus
    delivery_address: str | None
    notes: str | None
    raw_message: str
    wa_message_id: str | None
    created_at: datetime
    updated_at: datetime
    items: list[OrderItemOut] = []

    class Config:
        from_attributes = True


class OrderStatusUpdate(BaseModel):
    status: OrderStatus


class OrderListParams(BaseModel):
    status: OrderStatus | None = None
    phone: str | None = None
    skip: int = 0
    limit: int = 50
