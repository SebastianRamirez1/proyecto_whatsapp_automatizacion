export type OrderStatus =
  | "recibido"
  | "confirmado"
  | "en_preparacion"
  | "despachado"
  | "entregado"
  | "cancelado";

export const VALID_TRANSITIONS: Record<OrderStatus, OrderStatus[]> = {
  recibido: ["confirmado", "cancelado"],
  confirmado: ["en_preparacion", "cancelado"],
  en_preparacion: ["despachado", "cancelado"],
  despachado: ["entregado"],
  entregado: [],
  cancelado: [],
};

export const STATUS_LABEL: Record<OrderStatus, string> = {
  recibido: "Recibido",
  confirmado: "Confirmado",
  en_preparacion: "En preparación",
  despachado: "Despachado",
  entregado: "Entregado",
  cancelado: "Cancelado",
};

export const STATUS_COLORS: Record<OrderStatus, string> = {
  recibido: "bg-blue-100 text-blue-800 border-blue-200",
  confirmado: "bg-yellow-100 text-yellow-800 border-yellow-200",
  en_preparacion: "bg-orange-100 text-orange-800 border-orange-200",
  despachado: "bg-purple-100 text-purple-800 border-purple-200",
  entregado: "bg-green-100 text-green-800 border-green-200",
  cancelado: "bg-red-100 text-red-800 border-red-200",
};

export const STATUS_CHART_COLORS: Record<OrderStatus, string> = {
  recibido: "#3b82f6",
  confirmado: "#eab308",
  en_preparacion: "#f97316",
  despachado: "#a855f7",
  entregado: "#22c55e",
  cancelado: "#ef4444",
};

export interface ClientOut {
  id: number;
  phone: string;
  name: string | null;
}

export interface OrderItemOut {
  id: number;
  product_name: string;
  quantity: number;
  unit: string | null;
  unit_price: number | null;
}

export interface OrderOut {
  id: number;
  client_id: number;
  client: ClientOut;
  status: OrderStatus;
  delivery_address: string | null;
  notes: string | null;
  raw_message: string;
  wa_message_id: string;
  created_at: string;
  updated_at: string;
  items: OrderItemOut[];
}

export interface StatsResponse {
  total: number;
  by_status: Record<OrderStatus, number>;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
}
