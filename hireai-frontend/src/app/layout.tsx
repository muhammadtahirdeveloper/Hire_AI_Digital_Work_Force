import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { ThemeProvider } from "next-themes";
import { Toaster } from "react-hot-toast";
import { SessionProvider } from "@/components/shared/session-provider";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-geist-sans" });

export const metadata: Metadata = {
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
      <body className={`${inter.variable} font-sans`}>
        <SessionProvider>
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
        </SessionProvider>
      </body>
    </html>
  );
}
