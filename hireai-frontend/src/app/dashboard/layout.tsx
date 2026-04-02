"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/hooks/use-auth";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/dashboard/sidebar";
import { SetupWizard } from "@/components/dashboard/setup-wizard";
import { PageLoader } from "@/components/shared/page-loader";
import { Chatbot } from "@/components/shared/chatbot";
import { PushPrompt } from "@/components/shared/push-prompt";
import { setAuthToken, getAuthToken } from "@/lib/api";

function TrialExpiredModal() {
  const router = useRouter();
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="mx-4 w-full max-w-md rounded-2xl bg-white p-8 text-center shadow-2xl">
        <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-red-100">
          <svg className="h-8 w-8 text-red-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h2 className="text-xl font-bold text-gray-900">Trial Period Ended</h2>
        <p className="mt-3 text-sm text-gray-600">
          Your 7-day free trial has expired. Upgrade your plan to continue
          using your AI email agent.
        </p>
        <div className="mt-6 flex flex-col gap-3">
          <button
            onClick={() => router.push("/dashboard/billing")}
            className="w-full rounded-lg bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-700 transition-colors"
          >
            Upgrade Now
          </button>
          <button
            onClick={() => router.push("/dashboard")}
            className="w-full rounded-lg border border-gray-300 px-4 py-3 text-sm font-medium text-gray-700 hover:bg-gray-50 transition-colors"
          >
            View Dashboard
          </button>
        </div>
      </div>
    </div>
  );
}

function isTrialExpired(trialEndDate?: string): boolean {
  if (!trialEndDate) return false;
  return new Date(trialEndDate).getTime() < Date.now();
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { session, status } = useAuth();
  const [showTrialModal, setShowTrialModal] = useState(false);

  // Check trial expiry
  useEffect(() => {
    if (!session?.user) return;
    const tier = (session.user as Record<string, unknown>).tier as string;
    const trialEnd = (session.user as Record<string, unknown>).trialEndDate as string | undefined;
    if (tier === "trial" && isTrialExpired(trialEnd)) {
      setShowTrialModal(true);
    }
  }, [session?.user]);

  // Sync backend JWT from NextAuth session to localStorage (for Google login)
  useEffect(() => {
    if (!session?.user?.email) return;

    // If we already have a token, skip
    const existingToken = getAuthToken();
    if (existingToken) return;

    // Try to pull token from NextAuth session first
    const backendToken = (session as unknown as Record<string, unknown>).accessToken as string;
    if (backendToken) {
      setAuthToken(backendToken);
      return;
    }

    // Fallback: fetch fresh token from backend
    const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    if (!apiUrl) return;

    fetch(`${apiUrl}/auth/google-login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: session.user.email,
        name: session.user.name || "",
        image: session.user.image || "",
      }),
    })
      .then((r) => r.json())
      .then((data) => {
        const token =
          data?.data?.token ||
          data?.data?.access_token ||
          data?.token ||
          data?.access_token;
        if (token) {
          setAuthToken(token);
          window.location.reload();
        }
      })
      .catch((e) => console.error("Token sync failed:", e));
  }, [session?.user?.email]);

  if (status === "loading") {
    return <PageLoader />;
  }

  // Show setup wizard only if setupComplete is explicitly false
  if (session?.user && session.user.setupComplete === false) {
    return <SetupWizard />;
  }

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {showTrialModal && <TrialExpiredModal />}
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
      <PushPrompt />
    </div>
  );
}
