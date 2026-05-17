"use client";

import { useState } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import StatusBadge from "./StatusBadge";
import StatusDropdown from "./StatusDropdown";
import OrderDetailModal from "./OrderDetailModal";
import { useOrders } from "@/hooks/useOrders";
import { STATUS_LABEL, type OrderStatus, type OrderOut } from "@/types";
import { formatDate, formatPhone, truncate } from "@/lib/utils";
import { Eye } from "lucide-react";
import { Toaster } from "sonner";

const LIMIT = 10;
const ALL_STATUSES: OrderStatus[] = ["recibido", "confirmado", "en_preparacion", "despachado", "entregado", "cancelado"];

export default function OrdersTable() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const [statusFilter, setStatusFilter] = useState<OrderStatus | "">((searchParams.get("status") as OrderStatus) || "");
  const [phoneFilter, setPhoneFilter] = useState("");
  const [page, setPage] = useState(0);
  const [selectedOrder, setSelectedOrder] = useState<OrderOut | null>(null);

  const { orders, isLoading, refresh } = useOrders({
    status: statusFilter || undefined,
    phone: phoneFilter || undefined,
    skip: page * LIMIT,
    limit: LIMIT,
  });

  function handleStatusFilter(value: string) {
    setStatusFilter(value === "todos" ? "" : value as OrderStatus);
    setPage(0);
    if (value !== "todos") {
      router.replace(`/dashboard/orders?status=${value}`);
    } else {
      router.replace("/dashboard/orders");
    }
  }

  return (
    <>
      <Toaster richColors position="top-right" />

      {/* Filtros */}
      <div className="flex gap-3 mb-4 flex-wrap">
        <Select value={statusFilter || "todos"} onValueChange={handleStatusFilter}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Todos los estados" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="todos">Todos los estados</SelectItem>
            {ALL_STATUSES.map((s) => (
              <SelectItem key={s} value={s}>{STATUS_LABEL[s]}</SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Input
          placeholder="Buscar por teléfono…"
          className="w-52"
          value={phoneFilter}
          onChange={(e) => { setPhoneFilter(e.target.value); setPage(0); }}
        />
      </div>

      {/* Tabla */}
      <div className="bg-white rounded-xl border overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-zinc-50">
              <TableHead className="w-12">#</TableHead>
              <TableHead>Cliente</TableHead>
              <TableHead>Mensaje</TableHead>
              <TableHead>Estado</TableHead>
              <TableHead>Fecha</TableHead>
              <TableHead>Cambiar estado</TableHead>
              <TableHead className="w-10"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <TableRow key={i}>
                  {Array.from({ length: 7 }).map((_, j) => (
                    <TableCell key={j}><Skeleton className="h-4 w-full" /></TableCell>
                  ))}
                </TableRow>
              ))
            ) : orders.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-zinc-400 py-12">
                  No hay pedidos{statusFilter ? ` con estado "${STATUS_LABEL[statusFilter]}"` : ""}
                </TableCell>
              </TableRow>
            ) : (
              orders.map((order) => (
                <TableRow key={order.id} className="hover:bg-zinc-50">
                  <TableCell className="font-mono text-xs text-zinc-500">#{order.id}</TableCell>
                  <TableCell>
                    <div>
                      <p className="font-medium text-xs">{order.client.name || "—"}</p>
                      <p className="text-xs text-zinc-400">{formatPhone(order.client.phone)}</p>
                    </div>
                  </TableCell>
                  <TableCell className="text-xs text-zinc-600 max-w-xs">
                    {truncate(order.raw_message, 55)}
                  </TableCell>
                  <TableCell><StatusBadge status={order.status} /></TableCell>
                  <TableCell className="text-xs text-zinc-400 whitespace-nowrap">
                    {formatDate(order.created_at)}
                  </TableCell>
                  <TableCell>
                    <StatusDropdown order={order} onUpdated={refresh} />
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setSelectedOrder(order)}>
                      <Eye className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Paginación */}
      <div className="flex justify-between items-center mt-4">
        <p className="text-xs text-zinc-400">
          {isLoading ? "Cargando…" : `${orders.length} pedido(s) en esta página`}
        </p>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0}>
            Anterior
          </Button>
          <Button variant="outline" size="sm" onClick={() => setPage((p) => p + 1)} disabled={orders.length < LIMIT}>
            Siguiente
          </Button>
        </div>
      </div>

      <OrderDetailModal order={selectedOrder} onClose={() => setSelectedOrder(null)} />
    </>
  );
}
