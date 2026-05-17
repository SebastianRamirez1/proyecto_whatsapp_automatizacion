"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, ShoppingBasket } from "lucide-react";
import { cn } from "@/lib/utils";

const links = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/dashboard/orders", label: "Pedidos", icon: ShoppingBasket },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-52 border-r bg-zinc-50 flex flex-col gap-1 p-3 shrink-0">
      {links.map(({ href, label, icon: Icon }) => (
        <Link
          key={href}
          href={href}
          className={cn(
            "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors",
            pathname === href
              ? "bg-zinc-900 text-white"
              : "text-zinc-600 hover:bg-zinc-200 hover:text-zinc-900"
          )}
        >
          <Icon className="h-4 w-4" />
          {label}
        </Link>
      ))}
    </aside>
  );
}
