"use client";

import React, { createContext, useContext, useState, useEffect } from "react";
import { api } from "@/lib/api";

// --- Types ---

export interface TenantConfig {
  id?: string;
  brand_name: string;
  logo_url: string;
  primary_color: string;
  secondary_color: string;
  support_email: string;
  slug?: string;
  domain?: string;
  is_default: boolean;
}

const DEFAULT_CONFIG: TenantConfig = {
  brand_name: "HireAI",
  logo_url: "/logo.svg",
  primary_color: "#2563eb",
  secondary_color: "#1e40af",
  support_email: "hireaidigitalemployee@gmail.com",
  is_default: true,
};

interface TenantContextValue {
  tenant: TenantConfig;
  isWhiteLabel: boolean;
  brandName: string;
}

const TenantContext = createContext<TenantContextValue>({
  tenant: DEFAULT_CONFIG,
  isWhiteLabel: false,
  brandName: "HireAI",
});

// --- Helpers ---

function getSubdomainSlug(): string {
  if (typeof window === "undefined") return "";
  const hostname = window.location.hostname;
  // Match: slug.hireai.app or slug.hireai-frontend.vercel.app
  const parts = hostname.split(".");
  if (parts.length >= 3) {
    const slug = parts[0];
    // Ignore common prefixes
    if (["www", "app", "dashboard", "hireai-frontend"].includes(slug)) return "";
    return slug;
  }
  return "";
}

function getCustomDomain(): string {
  if (typeof window === "undefined") return "";
  const hostname = window.location.hostname;
  // If not a *.hireai.app or *.vercel.app domain, it's custom
  if (
    hostname.endsWith(".hireai.app") ||
    hostname.endsWith(".vercel.app") ||
    hostname === "localhost" ||
    hostname === "127.0.0.1"
  ) {
    return "";
  }
  return hostname;
}

// --- Provider ---

export function TenantProvider({ children }: { children: React.ReactNode }) {
  const [tenant, setTenant] = useState<TenantConfig>(DEFAULT_CONFIG);

  useEffect(() => {
    const slug = getSubdomainSlug();
    const domain = getCustomDomain();

    if (!slug && !domain) return; // Default HireAI, no fetch needed

    const params = new URLSearchParams();
    if (slug) params.set("slug", slug);
    if (domain) params.set("domain", domain);

    api
      .get(`/api/tenant/config?${params.toString()}`)
      .then((res) => {
        const data = res?.data;
        if (data && !data.is_default) {
          setTenant(data);
          // Apply custom CSS variables for branding
          document.documentElement.style.setProperty("--navy", data.primary_color);
          document.documentElement.style.setProperty("--navy-hover", data.secondary_color);
        }
      })
      .catch(() => {
        // Silently fall back to default
      });
  }, []);

  const isWhiteLabel = !tenant.is_default;
  const brandName = tenant.brand_name || "HireAI";

  return (
    <TenantContext.Provider value={{ tenant, isWhiteLabel, brandName }}>
      {children}
    </TenantContext.Provider>
  );
}

// --- Hook ---

export function useTenant() {
  return useContext(TenantContext);
}
