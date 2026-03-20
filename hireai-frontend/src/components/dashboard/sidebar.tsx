"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession } from "next-auth/react";
import {
  LayoutDashboard,
  Bot,
  Mail,
  BarChart3,
  Settings,
  CreditCard,
  Menu,
  X,
  Star,
  Shield,
  Users,
  Kanban,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/shared/theme-toggle";
import { ReviewModal } from "@/components/shared/review-modal";

const navItems = [
  { href: "/dashboard", icon: LayoutDashboard, label: "Overview" },
  { href: "/dashboard/agent", icon: Bot, label: "Agent" },
  { href: "/dashboard/emails", icon: Mail, label: "Emails" },
  { href: "/dashboard/contacts", icon: Users, label: "Contacts" },
  { href: "/dashboard/pipeline", icon: Kanban, label: "Pipeline" },
  { href: "/dashboard/analytics", icon: BarChart3, label: "Analytics" },
  { href: "/dashboard/settings", icon: Settings, label: "Settings" },
  { href: "/dashboard/billing", icon: CreditCard, label: "Billing" },
];

const ADMIN_EMAIL = "hireaidigitalemployee@gmail.com";

export function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);
  const { data: session } = useSession();
  const pathname = usePathname();
  const isAdmin = session?.user?.email === ADMIN_EMAIL;

  const sidebarContent = (
    <div className="flex h-full flex-col">
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 border-b border-border px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-navy text-white font-bold text-sm">
          H
        </div>
        <span className="text-lg font-bold text-text">HireAI</span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          const isActive =
            item.href === "/dashboard"
              ? pathname === "/dashboard"
              : pathname.startsWith(item.href);

          return (
            <Link
              key={item.href}
              href={item.href}
              onClick={() => setMobileOpen(false)}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                isActive
                  ? "bg-navy text-white"
                  : "text-text-3 hover:bg-background-2 hover:text-text"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
        {isAdmin && (
          <>
            <div className="mx-3 my-2 border-t border-border" />
            <Link
              href="/dashboard/admin"
              onClick={() => setMobileOpen(false)}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                pathname.startsWith("/dashboard/admin")
                  ? "bg-navy text-white"
                  : "text-text-3 hover:bg-background-2 hover:text-text"
              )}
            >
              <Shield className="h-4 w-4" />
              Admin
            </Link>
          </>
        )}
      </nav>

      {/* Agent Status */}
      <div className="border-t border-border px-4 py-3">
        <div className="flex items-center gap-2 rounded-lg bg-background-1 px-3 py-2">
          <span className="relative flex h-2.5 w-2.5">
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
            <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-green-500" />
          </span>
          <span className="text-xs font-medium text-text-2">Agent Live</span>
        </div>
      </div>

      {/* Rate HireAI */}
      <div className="border-t border-border px-4 py-3">
        <button
          onClick={() => setReviewOpen(true)}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-text-3 transition-colors hover:bg-background-2 hover:text-text"
        >
          <Star className="h-4 w-4" />
          Rate HireAI
        </button>
      </div>

      {/* Theme Toggle */}
      <div className="border-t border-border px-4 py-3">
        <ThemeToggle />
      </div>
    </div>
  );

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setMobileOpen(true)}
        className="fixed left-4 top-4 z-40 inline-flex h-10 w-10 items-center justify-center rounded-lg border border-border bg-background shadow-sm lg:hidden"
        aria-label="Open sidebar"
      >
        <Menu className="h-5 w-5 text-text" />
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Mobile sidebar */}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 border-r border-border bg-background transition-transform duration-200 lg:hidden",
          mobileOpen ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <button
          onClick={() => setMobileOpen(false)}
          className="absolute right-3 top-4 inline-flex h-8 w-8 items-center justify-center rounded-lg text-text-3 hover:bg-background-2"
          aria-label="Close sidebar"
        >
          <X className="h-4 w-4" />
        </button>
        {sidebarContent}
      </aside>

      {/* Desktop sidebar */}
      <aside className="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col border-r border-border bg-background">
        {sidebarContent}
      </aside>

      {/* Review Modal */}
      <ReviewModal open={reviewOpen} onClose={() => setReviewOpen(false)} />
    </>
  );
}
