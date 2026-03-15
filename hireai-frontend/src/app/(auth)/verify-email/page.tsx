"use client";

import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [status, setStatus] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!token) {
      setStatus("error");
      setMessage("Invalid verification link. No token provided.");
      return;
    }

    const verify = async () => {
      try {
        const res = await fetch(`${API_URL}/auth/verify-email?token=${token}`);
        const data = await res.json();

        if (res.ok) {
          setStatus("success");
          setMessage(data.message || "Email verified successfully!");
        } else {
          setStatus("error");
          setMessage(data.detail || "Verification failed. The link may be expired.");
        }
      } catch {
        setStatus("error");
        setMessage("Something went wrong. Please try again.");
      }
    };

    verify();
  }, [token]);

  return (
    <div className="w-full max-w-md">
      <div className="rounded-xl border border-border bg-background p-8 shadow-sm">
        <div className="flex justify-center">
          <div className="flex items-center gap-2">
            <img src="/logo.svg" alt="HireAI" className="h-10 w-10 dark:invert" />
            <span className="text-xl font-bold text-text">HireAI</span>
          </div>
        </div>

        <div className="mt-8 flex justify-center">
          {status === "loading" && (
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-navy/10">
              <Loader2 className="h-8 w-8 animate-spin text-navy" />
            </div>
          )}
          {status === "success" && (
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/10">
              <CheckCircle2 className="h-8 w-8 text-emerald-500" />
            </div>
          )}
          {status === "error" && (
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-danger/10">
              <XCircle className="h-8 w-8 text-danger" />
            </div>
          )}
        </div>

        <div className="mt-6 text-center">
          <h1 className="text-2xl font-bold text-text">
            {status === "loading" && "Verifying your email..."}
            {status === "success" && "Email verified!"}
            {status === "error" && "Verification failed"}
          </h1>
          <p className="mt-2 text-sm text-text-3">{message}</p>
        </div>

        <div className="mt-6">
          {status === "success" && (
            <Link href="/login">
              <Button className="w-full">Sign in to your account</Button>
            </Link>
          )}
          {status === "error" && (
            <Link href="/signup">
              <Button variant="outline" className="w-full">
                Back to signup
              </Button>
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <div className="w-full max-w-md">
          <div className="rounded-xl border border-border bg-background p-8 shadow-sm">
            <div className="flex justify-center">
              <Loader2 className="h-8 w-8 animate-spin text-navy" />
            </div>
          </div>
        </div>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}
