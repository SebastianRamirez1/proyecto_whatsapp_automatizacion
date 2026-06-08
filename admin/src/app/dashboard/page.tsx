import StatsCards from "@/components/dashboard/StatsCards";
import StatusChart from "@/components/dashboard/StatusChart";

export default function DashboardPage() {
  return (
    <div className="space-y-6 max-w-5xl">
      <div>
        <h1 className="text-2xl font-bold text-zinc-900">Dashboard</h1>
        <p className="text-sm text-zinc-500 mt-1">Resumen de pedidos en tiempo real</p>
      </div>
      <StatsCards />
      <StatusChart />
    </div>
  );
}
