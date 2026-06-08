"use client";

import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import StatusBadge from "./StatusBadge";
import { formatDate, formatPhone } from "@/lib/utils";
import type { OrderOut } from "@/types";

interface Props {
  order: OrderOut | null;
  onClose: () => void;
}

export default function OrderDetailModal({ order, onClose }: Props) {
  if (!order) return null;

  const clientName = order.client.name || formatPhone(order.client.phone);

  return (
    <Dialog open={!!order} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-3">
            Pedido #{order.id}
            <StatusBadge status={order.status} />
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 text-sm">
          {/* Cliente */}
          <div>
            <p className="font-medium text-zinc-500 mb-1">Cliente</p>
            <p className="font-semibold">{clientName}</p>
            <a
              href={`https://wa.me/${order.client.phone}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-green-600 hover:underline text-xs"
            >
              {formatPhone(order.client.phone)} — Abrir WhatsApp
            </a>
          </div>

          <Separator />

          {/* Items */}
          <div>
            <p className="font-medium text-zinc-500 mb-2">Productos</p>
            <table className="w-full text-xs">
              <thead>
                <tr className="text-left text-zinc-400">
                  <th className="pb-1">Producto</th>
                  <th className="pb-1">Cantidad</th>
                  <th className="pb-1">Unidad</th>
                  <th className="pb-1">Precio</th>
                </tr>
              </thead>
              <tbody>
                {order.items.map((item) => (
                  <tr key={item.id} className="border-t">
                    <td className="py-1 font-medium">{item.product_name}</td>
                    <td className="py-1">{item.quantity}</td>
                    <td className="py-1">{item.unit ?? "—"}</td>
                    <td className="py-1">{item.unit_price != null ? `$${item.unit_price}` : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <Separator />

          {/* Dirección y notas */}
          {order.delivery_address && (
            <div>
              <p className="font-medium text-zinc-500 mb-1">Dirección de entrega</p>
              <p>{order.delivery_address}</p>
            </div>
          )}
          {order.notes && (
            <div>
              <p className="font-medium text-zinc-500 mb-1">Notas</p>
              <p>{order.notes}</p>
            </div>
          )}

          {/* Mensaje original */}
          <div>
            <p className="font-medium text-zinc-500 mb-1">Mensaje original</p>
            <pre className="bg-zinc-100 rounded p-2 text-xs whitespace-pre-wrap">{order.raw_message}</pre>
          </div>

          <Separator />

          {/* Fechas */}
          <div className="flex justify-between text-xs text-zinc-400">
            <span>Creado: {formatDate(order.created_at)}</span>
            <span>Actualizado: {formatDate(order.updated_at)}</span>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
