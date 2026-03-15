"use client";

import { useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { Lock, Eye, EyeOff, CheckCircle2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function ResetPasswordPage() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState(false);

  if (!token) {
    return (
      <div className="w-full max-w-md">
        <div className="rounded-xl border border-border bg-background p-8 shadow-sm text-center">
          <h1 className="text-2xl font-bold text-text">Invalid link</h1>
          <p className="mt-2 text-sm text-text-3">
            This password reset link is invalid or has expired.
          </p>
          <Link href="/forgot-password" className="mt-4 inline-block">
            <Button variant="outline">Request a new link</Button>
          </Link>
        </div>
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match");
      return;
    }

    if (password.length < 8) {
      setError("Password must be at least 8 characters");
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_URL}/auth/reset-password`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      });

      if (res.ok) {
        setSuccess(true);
      } else {
        const data = await res.json();
        setError(data.detail || "Reset failed. The link may be expired.");
      }
    } catch {
      setError("Something went wrong. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="w-full max-w-md">
        <div className="rounded-xl border border-border bg-background p-8 shadow-sm">
          <div className="flex justify-center">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-500/10">
              <CheckCircle2 className="h-8 w-8 text-emerald-500" />
            </div>
          </div>
          <div className="mt-6 text-center">
            <h1 className="text-2xl font-bold text-text">Password reset!</h1>
            <p className="mt-2 text-sm text-text-3">
              Your password has been updated successfully.
            </p>
          </div>
          <div className="mt-6">
            <Link href="/login">
              <Button className="w-full">Sign in with new password</Button>
            </Link>
          </div>
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
          <h1 className="text-2xl font-bold text-text">Reset password</h1>
          <p className="mt-1 text-sm text-text-3">
            Enter your new password below.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="mt-6 space-y-4">
          {error && (
            <div className="rounded-lg bg-danger/10 px-3 py-2 text-sm text-danger">
              {error}
            </div>
          )}

          <Input
            label="New password"
            type={showPassword ? "text" : "password"}
            placeholder="Min. 8 characters"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            prefixIcon={<Lock className="h-4 w-4" />}
            suffixIcon={
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="pointer-events-auto cursor-pointer"
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            }
            required
          />

          <Input
            label="Confirm new password"
            type={showPassword ? "text" : "password"}
            placeholder="Re-enter password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            prefixIcon={<Lock className="h-4 w-4" />}
            required
          />

          <Button type="submit" loading={loading} className="w-full">
            Reset password
          </Button>
        </form>
      </div>
    </div>
  );
}
