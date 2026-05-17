import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.session import Base
from app.models.order import OrderStatus
from app.schemas.interpretation import InterpretationResult, MessageIntent, OrderItemExtracted
from app.services.orders import (
    create_order_from_interpretation,
    get_or_create_client,
    get_status_notification_message,
    transition_order_status,
)

# SQLite en memoria para tests — no requiere PostgreSQL corriendo
TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture(scope="function")
def db():
    engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


@pytest.fixture()
def sample_interpretation() -> InterpretationResult:
    return InterpretationResult(
        intent=MessageIntent.nuevo_pedido,
        items=[
            OrderItemExtracted(producto="Huevos AA", cantidad=3, unidad="cubeta"),
            OrderItemExtracted(producto="Huevos B", cantidad=1, unidad="cubeta"),
        ],
        direccion_entrega="Calle 50 # 30-10",
        observaciones="Dejar en portería",
        confianza=0.95,
    )


class TestGetOrCreateClient:
    def test_creates_new_client(self, db):
        client = get_or_create_client(db, phone="573001234567", name="Juan")
        assert client.id is not None
        assert client.phone == "573001234567"
        assert client.name == "Juan"

    def test_returns_existing_client(self, db):
        c1 = get_or_create_client(db, phone="573001234567")
        c2 = get_or_create_client(db, phone="573001234567")
        assert c1.id == c2.id

    def test_creates_different_clients_for_different_phones(self, db):
        c1 = get_or_create_client(db, phone="573001111111")
        c2 = get_or_create_client(db, phone="573002222222")
        assert c1.id != c2.id


class TestCreateOrder:
    def test_creates_order_with_correct_status(self, db, sample_interpretation):
        client = get_or_create_client(db, phone="573001234567")
        order = create_order_from_interpretation(
            db, client, sample_interpretation, raw_message="3 cubetas AA y 1 B en Calle 50"
        )
        assert order.id is not None
        assert order.status == OrderStatus.recibido
        assert order.client_id == client.id

    def test_creates_order_items(self, db, sample_interpretation):
        client = get_or_create_client(db, phone="573001234567")
        order = create_order_from_interpretation(
            db, client, sample_interpretation, raw_message="pedido"
        )
        assert len(order.items) == 2
        products = {item.product_name for item in order.items}
        assert "Huevos AA" in products
        assert "Huevos B" in products

    def test_stores_delivery_address(self, db, sample_interpretation):
        client = get_or_create_client(db, phone="573001234567")
        order = create_order_from_interpretation(
            db, client, sample_interpretation, raw_message="pedido"
        )
        assert order.delivery_address == "Calle 50 # 30-10"

    def test_stores_wa_message_id(self, db, sample_interpretation):
        client = get_or_create_client(db, phone="573001234567")
        order = create_order_from_interpretation(
            db, client, sample_interpretation,
            raw_message="pedido", wa_message_id="wamid.abc123"
        )
        assert order.wa_message_id == "wamid.abc123"


class TestStateMachine:
    def _create_order(self, db, sample_interpretation):
        client = get_or_create_client(db, phone="573009999999")
        return create_order_from_interpretation(db, client, sample_interpretation, raw_message="test")

    def test_valid_transition_recibido_to_confirmado(self, db, sample_interpretation):
        order = self._create_order(db, sample_interpretation)
        order = transition_order_status(db, order, OrderStatus.confirmado)
        assert order.status == OrderStatus.confirmado

    def test_valid_full_flow(self, db, sample_interpretation):
        order = self._create_order(db, sample_interpretation)
        for new_status in [
            OrderStatus.confirmado,
            OrderStatus.en_preparacion,
            OrderStatus.despachado,
            OrderStatus.entregado,
        ]:
            order = transition_order_status(db, order, new_status)
        assert order.status == OrderStatus.entregado

    def test_invalid_transition_raises_value_error(self, db, sample_interpretation):
        order = self._create_order(db, sample_interpretation)
        with pytest.raises(ValueError, match="Transición inválida"):
            transition_order_status(db, order, OrderStatus.entregado)

    def test_cannot_transition_from_entregado(self, db, sample_interpretation):
        order = self._create_order(db, sample_interpretation)
        for s in [OrderStatus.confirmado, OrderStatus.en_preparacion,
                  OrderStatus.despachado, OrderStatus.entregado]:
            order = transition_order_status(db, order, s)
        with pytest.raises(ValueError):
            transition_order_status(db, order, OrderStatus.cancelado)

    def test_cancel_from_recibido(self, db, sample_interpretation):
        order = self._create_order(db, sample_interpretation)
        order = transition_order_status(db, order, OrderStatus.cancelado)
        assert order.status == OrderStatus.cancelado


class TestStatusNotifications:
    def test_notification_message_contains_order_id(self, db, sample_interpretation):
        client = get_or_create_client(db, phone="573001234567")
        order = create_order_from_interpretation(db, client, sample_interpretation, raw_message="x")
        transition_order_status(db, order, OrderStatus.confirmado)
        msg = get_status_notification_message(order)
        assert str(order.id) in msg
        assert "confirmado" in msg.lower()

    def test_no_notification_for_recibido(self, db, sample_interpretation):
        client = get_or_create_client(db, phone="573001234567")
        order = create_order_from_interpretation(db, client, sample_interpretation, raw_message="x")
        msg = get_status_notification_message(order)
        assert msg is None
