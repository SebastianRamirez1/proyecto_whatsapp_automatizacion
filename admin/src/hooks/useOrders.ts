import useSWR from "swr";
import { apiFetch } from "@/lib/api";
import type { OrderOut, OrderStatus } from "@/types";

interface UseOrdersParams {
  status?: OrderStatus | "";
  phone?: string;
  skip?: number;
  limit?: number;
}

export function useOrders(params: UseOrdersParams = {}) {
  const query = new URLSearchParams();
  if (params.status) query.set("status", params.status);
  if (params.phone) query.set("phone", params.phone);
  if (params.skip != null) query.set("skip", String(params.skip));
  if (params.limit != null) query.set("limit", String(params.limit));

  const key = `/api/v1/orders?${query.toString()}`;

  const { data, error, isLoading, mutate } = useSWR<OrderOut[]>(
    key,
    (url: string) => apiFetch<OrderOut[]>(url),
    { refreshInterval: 30_000 }
  );

  return { orders: data ?? [], error, isLoading, refresh: mutate };
}
