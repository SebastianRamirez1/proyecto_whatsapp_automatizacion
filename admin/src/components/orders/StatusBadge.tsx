import { STATUS_COLORS, STATUS_LABEL, type OrderStatus } from "@/types";
import { cn } from "@/lib/utils";

export default function StatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span className={cn("text-xs px-2 py-0.5 rounded-full border font-medium", STATUS_COLORS[status])}>
      {STATUS_LABEL[status]}
    </span>
  );
}
