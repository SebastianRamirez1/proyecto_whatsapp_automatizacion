"use client";

import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { useOrderStats } from "@/hooks/useOrderStats";
import { Skeleton } from "@/components/ui/skeleton";
import { STATUS_LABEL, STATUS_CHART_COLORS, type OrderStatus } from "@/types";

export default function StatusChart() {
  const { stats, isLoading } = useOrderStats();

  if (isLoading) return <Skeleton className="h-56 w-full rounded-xl" />;
  if (!stats) return null;

  const data = Object.entries(stats.by_status).map(([status, count]) => ({
    name: STATUS_LABEL[status as OrderStatus],
    value: count,
    color: STATUS_CHART_COLORS[status as OrderStatus],
  }));

  return (
    <div className="bg-white rounded-xl border p-4">
      <p className="text-sm font-medium text-zinc-500 mb-4">Pedidos por estado</p>
      <ResponsiveContainer width="100%" height={200}>
        <BarChart data={data} barSize={36}>
          <XAxis dataKey="name" tick={{ fontSize: 11 }} />
          <YAxis allowDecimals={false} tick={{ fontSize: 11 }} />
          <Tooltip />
          <Bar dataKey="value" radius={[4, 4, 0, 0]}>
            {data.map((entry, i) => (
              <Cell key={i} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
