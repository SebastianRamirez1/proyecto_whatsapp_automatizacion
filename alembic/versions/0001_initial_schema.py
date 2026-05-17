"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-17

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("phone", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_clients_id", "clients", ["id"])
    op.create_index("ix_clients_phone", "clients", ["phone"], unique=True)

    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("client_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "recibido",
                "confirmado",
                "en_preparacion",
                "despachado",
                "entregado",
                "cancelado",
                name="orderstatus",
            ),
            nullable=False,
        ),
        sa.Column("raw_message", sa.Text(), nullable=False),
        sa.Column("delivery_address", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("wa_message_id", sa.String(length=100), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["clients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_orders_id", "orders", ["id"])

    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("product_name", sa.String(length=150), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit", sa.String(length=30), nullable=True),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_order_items_id", "order_items", ["id"])


def downgrade() -> None:
    op.drop_index("ix_order_items_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_orders_id", table_name="orders")
    op.drop_table("orders")
    op.drop_index("ix_clients_phone", table_name="clients")
    op.drop_index("ix_clients_id", table_name="clients")
    op.drop_table("clients")
    op.execute("DROP TYPE IF EXISTS orderstatus")
