import { Suspense } from "react";
import OrdersTable from "@/components/orders/OrdersTable";

export default function OrdersPage() {
  return (
    <div className="space-y-4 max-w-6xl">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900">Pedidos</h1>
        <p className="text-sm text-zinc-500 mt-1">Gestiona y actualiza el estado de cada pedido</p>
      </div>
      <Suspense>
        <OrdersTable />
      </Suspense>
    </div>
  );
}
