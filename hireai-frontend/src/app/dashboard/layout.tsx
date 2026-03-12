"use client";

import { useSession } from "next-auth/react";
import { Sidebar } from "@/components/dashboard/sidebar";
import { SetupWizard } from "@/components/dashboard/setup-wizard";
import { PageLoader } from "@/components/shared/page-loader";
import { Chatbot } from "@/components/shared/chatbot";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { data: session, status } = useSession();

  if (status === "loading") {
    return <PageLoader />;
  }

  // Show setup wizard for new users
  if (session?.user && !session.user.setupComplete) {
    return <SetupWizard />;
  }

  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <main className="lg:pl-64">
        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
          {children}
        </div>
      </main>
      <Chatbot />
    </div>
  );
}
