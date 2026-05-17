from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageIntent(str, Enum):
    nuevo_pedido = "nuevo_pedido"
    consulta_estado = "consulta_estado"
    cancelacion = "cancelacion"
    saludo = "saludo"
    ambiguo = "ambiguo"


class OrderItemExtracted(BaseModel):
    producto: str = Field(description="Nombre del producto")
    cantidad: int = Field(description="Cantidad solicitada")
    unidad: str | None = Field(default=None, description="Unidad de medida: cubeta, docena, unidad, kg, etc.")


class InterpretationResult(BaseModel):
    intent: MessageIntent
    items: list[OrderItemExtracted] = Field(default_factory=list)
    direccion_entrega: str | None = None
    observaciones: str | None = None
    confianza: float = Field(ge=0.0, le=1.0, description="Nivel de confianza 0-1")
    razon_ambiguo: str | None = Field(
        default=None,
        description="Si intent=ambiguo, explica qué falta para procesar el pedido",
    )


class InterpretationRequest(BaseModel):
    message: str
    phone: str
    context: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Mensajes previos del hilo para dar contexto al modelo",
    )
