"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useAuth } from "@/hooks/use-auth";
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
  Building2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/shared/theme-toggle";
import { ReviewModal } from "@/components/shared/review-modal";
import { useLocale, LOCALES } from "@/lib/i18n";
import { useTenant } from "@/lib/tenant";

const navItems = [
  { href: "/dashboard", icon: LayoutDashboard, labelKey: "nav.overview" },
  { href: "/dashboard/agent", icon: Bot, labelKey: "nav.agent" },
  { href: "/dashboard/emails", icon: Mail, labelKey: "nav.emails" },
  { href: "/dashboard/contacts", icon: Users, labelKey: "nav.contacts" },
  { href: "/dashboard/pipeline", icon: Kanban, labelKey: "nav.pipeline" },
  { href: "/dashboard/analytics", icon: BarChart3, labelKey: "nav.analytics" },
  { href: "/dashboard/settings", icon: Settings, labelKey: "nav.settings" },
  { href: "/dashboard/billing", icon: CreditCard, labelKey: "nav.billing" },
];

const ADMIN_EMAIL = "hireaidigitalemployee@gmail.com";

export function Sidebar() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [langOpen, setLangOpen] = useState(false);
  const { session } = useAuth();
  const pathname = usePathname();
  const isAdmin = session?.user?.email === ADMIN_EMAIL;
  const { t, locale, setLocale, localeInfo } = useLocale();
  const { brandName, tenant, isWhiteLabel } = useTenant();

  const sidebarContent = (
    <div className="flex h-full flex-col">
      {/* Logo */}
      <div className="flex h-16 items-center gap-2 border-b border-border px-6">
        {isWhiteLabel && tenant.logo_url ? (
          <img src={tenant.logo_url} alt={brandName} className="h-8 w-8 rounded-lg object-contain" />
        ) : (
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-navy text-white font-bold text-sm">
            {brandName[0]}
          </div>
        )}
        <span className="text-lg font-bold text-text">{brandName}</span>
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
              {t(item.labelKey)}
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
              {t("nav.admin")}
            </Link>
          </>
        )}
        {isWhiteLabel && (
          <>
            <div className="mx-3 my-2 border-t border-border" />
            <Link
              href="/dashboard/tenant"
              onClick={() => setMobileOpen(false)}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                pathname.startsWith("/dashboard/tenant")
                  ? "bg-navy text-white"
                  : "text-text-3 hover:bg-background-2 hover:text-text"
              )}
            >
              <Building2 className="h-4 w-4" />
              Organization
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
          <span className="text-xs font-medium text-text-2">{t("dashboard.agent_live")}</span>
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

      {/* Language Switcher */}
      <div className="relative border-t border-border px-4 py-3">
        <button
          onClick={() => setLangOpen(!langOpen)}
          className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-text-3 transition-colors hover:bg-background-2 hover:text-text"
        >
          <span className="text-sm">{localeInfo.nativeName}</span>
          <span className="flex-1 text-left rtl:text-right text-text-4">{localeInfo.name}</span>
          <svg className={cn("h-3 w-3 transition-transform", langOpen && "rotate-180")} fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" /></svg>
        </button>
        {langOpen && (
          <div className="absolute bottom-full left-4 right-4 mb-1 rounded-lg border border-border bg-background shadow-lg z-50">
            {LOCALES.map((l) => (
              <button
                key={l.code}
                onClick={() => {
                  setLocale(l.code);
                  setLangOpen(false);
                }}
                className={cn(
                  "flex w-full items-center gap-2 px-3 py-2 text-xs transition-colors first:rounded-t-lg last:rounded-b-lg",
                  locale === l.code
                    ? "bg-navy/10 font-medium text-navy"
                    : "text-text-3 hover:bg-background-2 hover:text-text"
                )}
              >
                <span className="text-sm">{l.nativeName}</span>
                <span className="flex-1 text-left rtl:text-right">{l.name}</span>
                {locale === l.code && (
                  <span className="h-1.5 w-1.5 rounded-full bg-navy" />
                )}
              </button>
            ))}
          </div>
        )}
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
