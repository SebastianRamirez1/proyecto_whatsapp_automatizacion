"use client";

import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { LogOut } from "lucide-react";
import { removeToken } from "@/lib/auth";

export default function Navbar() {
  const router = useRouter();

  function handleLogout() {
    removeToken();
    router.push("/login");
  }

  return (
    <header className="h-14 border-b bg-white flex items-center justify-between px-6 shrink-0">
      <span className="font-semibold text-zinc-800">🥚 Distribuidora — Panel Admin</span>
      <Button variant="ghost" size="sm" onClick={handleLogout} className="gap-2 text-zinc-500">
        <LogOut className="h-4 w-4" />
        Salir
      </Button>
    </header>
  );
}
