"use client";

import { useState } from "react";
import Link from "next/link";
import { Mail, ArrowLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [sent, setSent] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/auth/forgot-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      });

      if (res.ok) {
        setSent(true);
      } else {
        const data = await res.json();
        setError(data.detail || "Something went wrong. Please try again.");
      }
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (sent) {
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
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-navy/10">
              <Mail className="h-8 w-8 text-navy" />
            </div>
          </div>

          <div className="mt-6 text-center">
            <h1 className="text-2xl font-bold text-text">Check your email</h1>
            <p className="mt-2 text-sm text-text-3">
              If an account exists for{" "}
              <span className="font-medium text-text">{email}</span>, we sent a
              password reset link.
            </p>
          </div>

          <p className="mt-6 text-center text-sm text-text-3">
            <Link href="/login" className="font-medium text-navy hover:underline">
              Back to login
            </Link>
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full max-w-md">
      <div className="rounded-xl border border-border bg-background p-8 shadow-sm">
        <div className="flex justify-center">
          <div className="flex items-center gap-2">
            <img src="/logo.svg" alt="HireAI" className="h-10 w-10 dark:invert" />
            <span className="text-xl font-bold text-text">HireAI</span>
          </div>
        </div>

        <div className="mt-6 text-center">
          <h1 className="text-2xl font-bold text-text">Forgot password?</h1>
          <p className="mt-1 text-sm text-text-3">
            Enter your email and we&apos;ll send you a reset link.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          {error && (
            <div className="rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger">
              {error}
            </div>
          )}

          <Input
            label="Email"
            type="email"
            placeholder="you@company.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            prefixIcon={<Mail className="h-4 w-4" />}
            required
          />

          <Button type="submit" loading={loading} className="w-full">
            Send reset link
          </Button>
        </form>

        <p className="mt-6 text-center text-sm text-text-3">
          <Link
            href="/login"
            className="inline-flex items-center gap-1 font-medium text-navy hover:underline"
          >
            <ArrowLeft className="h-3 w-3" />
            Back to login
          </Link>
        </p>
      </div>
    </div>
  );
}
