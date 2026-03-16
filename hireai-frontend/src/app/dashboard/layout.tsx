"use client";

import { useEffect } from "react";
import { useSession } from "next-auth/react";
import { Sidebar } from "@/components/dashboard/sidebar";
import { SetupWizard } from "@/components/dashboard/setup-wizard";
import { PageLoader } from "@/components/shared/page-loader";
import { Chatbot } from "@/components/shared/chatbot";
import { setAuthToken, getAuthToken } from "@/lib/api";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: session, status } = useSession();

  // Sync backend JWT from NextAuth session to localStorage (for Google login)
  useEffect(() => {
    const existing = getAuthToken();
    if (!existing && session) {
      const backendToken = (session as unknown as Record<string, unknown>).accessToken as string;
      if (backendToken) {
        setAuthToken(backendToken);
      }
    }
  }, [session]);

  if (status === "loading") {
    return <PageLoader />;
  }

  // Show setup wizard only if setupComplete is explicitly false
  if (session?.user && session.user.setupComplete === false) {
    return <SetupWizard />;
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      <Sidebar />
      <main className="lg:pl-64 flex-1">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          {children}
        </div>
      </main>
      <footer className="lg:pl-64 border-t border-border bg-background-1">
        <div className="mx-auto max-w-7xl px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex flex-col items-center justify-between gap-2 sm:flex-row">
            <p className="text-xs text-text-4">
              &copy; {new Date().getFullYear()} HireAI. All rights reserved.
            </p>
            <div className="flex gap-4 text-xs text-text-4">
              <a href="/privacy" className="hover:text-navy">Privacy</a>
              <a href="/terms" className="hover:text-navy">Terms</a>
              <a href="/docs" className="hover:text-navy">Docs</a>
              <a href="/contact" className="hover:text-navy">Contact</a>
            </div>
          </div>
        </div>
      </footer>
      <Chatbot />
    </div>
  );
}
