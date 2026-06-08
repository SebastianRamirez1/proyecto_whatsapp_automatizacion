"use client";

import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useOrderStats } from "@/hooks/useOrderStats";
import { STATUS_LABEL, STATUS_COLORS, type OrderStatus } from "@/types";

const STATUS_ORDER: OrderStatus[] = [
  "recibido", "confirmado", "en_preparacion", "despachado", "entregado", "cancelado",
];

export default function StatsCards() {
  const { stats, isLoading } = useOrderStats();
  const router = useRouter();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
        {Array.from({ length: 7 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 gap-4">
      <Card className="col-span-2 md:col-span-1 cursor-default">
        <CardHeader className="pb-1">
          <CardTitle className="text-sm font-medium text-zinc-500">Total pedidos</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-4xl font-bold text-zinc-900">{stats?.total ?? 0}</p>
        </CardContent>
      </Card>

      {STATUS_ORDER.map((status) => (
        <Card
          key={status}
          className="cursor-pointer hover:shadow-md transition-shadow"
          onClick={() => router.push(`/dashboard/orders?status=${status}`)}
        >
          <CardHeader className="pb-1">
            <CardTitle className="text-sm font-medium text-zinc-500">
              {STATUS_LABEL[status]}
            </CardTitle>
          </CardHeader>
          <CardContent className="flex items-end justify-between">
            <p className="text-3xl font-bold text-zinc-900">
              {stats?.by_status?.[status] ?? 0}
            </p>
            <span className={`text-xs px-2 py-0.5 rounded-full border font-medium ${STATUS_COLORS[status]}`}>
              {STATUS_LABEL[status]}
            </span>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
