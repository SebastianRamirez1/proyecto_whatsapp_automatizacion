import useSWR from "swr";
import { apiFetch } from "@/lib/api";
import type { StatsResponse } from "@/types";

export function useOrderStats() {
  const { data, error, isLoading, mutate } = useSWR<StatsResponse>(
    "/api/v1/orders/summary/stats",
    (url: string) => apiFetch<StatsResponse>(url),
    { refreshInterval: 30_000 }
  );
  return { stats: data, error, isLoading, refresh: mutate };
}
