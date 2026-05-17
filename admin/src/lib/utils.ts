import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(iso: string): string {
  const date = new Date(iso);
  const now = new Date();
  const diff = (now.getTime() - date.getTime()) / 1000;

  if (diff < 60) return "hace un momento";
  if (diff < 3600) return `hace ${Math.floor(diff / 60)} min`;
  if (diff < 86400) return `hace ${Math.floor(diff / 3600)} h`;
  if (diff < 604800) return `hace ${Math.floor(diff / 86400)} días`;

  return date.toLocaleDateString("es-CO", { day: "2-digit", month: "short", year: "numeric" });
}

export function formatPhone(phone: string): string {
  // 573002791360 → +57 300 279 1360
  if (phone.startsWith("57") && phone.length === 12) {
    return `+57 ${phone.slice(2, 5)} ${phone.slice(5, 8)} ${phone.slice(8)}`;
  }
  return `+${phone}`;
}

export function truncate(text: string, max = 50): string {
  return text.length > max ? text.slice(0, max) + "…" : text;
}
