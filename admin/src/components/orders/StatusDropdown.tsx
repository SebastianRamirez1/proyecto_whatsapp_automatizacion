"use client";

import { useState } from "react";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "@/components/ui/alert-dialog";
import { apiFetch } from "@/lib/api";
import { VALID_TRANSITIONS, STATUS_LABEL, type OrderStatus, type OrderOut } from "@/types";
import { toast } from "sonner";

interface Props {
  order: OrderOut;
  onUpdated: () => void;
}

export default function StatusDropdown({ order, onUpdated }: Props) {
  const [loading, setLoading] = useState(false);
  const [pendingStatus, setPendingStatus] = useState<OrderStatus | null>(null);

  const transitions = VALID_TRANSITIONS[order.status];

  if (transitions.length === 0) {
    return <span className="text-xs text-zinc-400 italic">Final</span>;
  }

  async function applyStatus(newStatus: OrderStatus) {
    setLoading(true);
    try {
      await apiFetch(`/api/v1/orders/${order.id}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
      });
      toast.success(`Pedido #${order.id} → ${STATUS_LABEL[newStatus]}`);
      onUpdated();
    } catch {
      toast.error("No se pudo cambiar el estado");
    } finally {
      setLoading(false);
      setPendingStatus(null);
    }
  }

  function handleChange(value: string) {
    const newStatus = value as OrderStatus;
    if (newStatus === "cancelado") {
      setPendingStatus(newStatus);
    } else {
      applyStatus(newStatus);
    }
  }

  return (
    <>
      <Select onValueChange={handleChange} disabled={loading}>
        <SelectTrigger className="h-7 text-xs w-36">
          <SelectValue placeholder={loading ? "Guardando…" : "Cambiar estado"} />
        </SelectTrigger>
        <SelectContent>
          {transitions.map((s) => (
            <SelectItem key={s} value={s} className="text-xs">
              {STATUS_LABEL[s]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>

      <AlertDialog open={!!pendingStatus} onOpenChange={() => setPendingStatus(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>¿Cancelar pedido #{order.id}?</AlertDialogTitle>
            <AlertDialogDescription>
              Esta acción enviará una notificación al cliente por WhatsApp. No se puede deshacer.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>No</AlertDialogCancel>
            <AlertDialogAction onClick={() => pendingStatus && applyStatus(pendingStatus)} className="bg-red-600 hover:bg-red-700">
              Sí, cancelar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
