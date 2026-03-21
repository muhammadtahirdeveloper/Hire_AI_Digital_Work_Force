import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ThemeProvider } from "next-themes";
import { Toaster } from "react-hot-toast";
import { SessionProvider } from "@/components/shared/session-provider";
import { PWAProvider } from "@/components/shared/pwa-provider";
import { LocaleProvider } from "@/lib/i18n";
import { TenantProvider } from "@/lib/tenant";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-geist-sans" });

export const metadata: Metadata = {
  manifest: "/manifest.json",
  themeColor: "#2563eb",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "HireAI",
  },
  icons: {
    icon: "/logo.svg",
    shortcut: "/logo.svg",
    apple: "/icon-192.png",
  },
  title: {
    default: "HireAI — Intelligent Email Agents",
    template: "%s | HireAI",
  },
  description:
    "AI agents that read, classify, and respond to your emails automatically. Powered by Claude AI.",
  keywords: [
    "AI email",
    "email automation",
    "Gmail agent",
    "HR agent",
    "email assistant",
    "AI inbox",
    "email management",
  ],
  openGraph: {
    title: "HireAI — Intelligent Email Agents",
    description:
      "AI agents that read, classify, and respond to your emails automatically.",
    siteName: "HireAI",
    type: "website",
    locale: "en_US",
  },
  twitter: {
    card: "summary_large_image",
    title: "HireAI — Intelligent Email Agents",
    description:
      "AI agents that read, classify, and respond to your emails automatically.",
  },
  robots: {
    index: true,
    follow: true,
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no, viewport-fit=cover" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="mobile-web-app-capable" content="yes" />
        <link rel="apple-touch-icon" href="/icon-192.png" />
      </head>
      <body className={`${inter.variable} font-sans`}>
        <SessionProvider>
          <LocaleProvider>
          <TenantProvider>
          <PWAProvider>
          <ThemeProvider
            attribute="class"
            defaultTheme="light"
            enableSystem={false}
            storageKey="hireai-theme"
            disableTransitionOnChange
          >
            {children}
            <Toaster
              position="top-right"
              toastOptions={{
                className: "!bg-background !text-text !border !border-border",
                duration: 4000,
              }}
            />
          </ThemeProvider>
          </PWAProvider>
          </TenantProvider>
          </LocaleProvider>
        </SessionProvider>
      </body>
    </html>
  );
}
