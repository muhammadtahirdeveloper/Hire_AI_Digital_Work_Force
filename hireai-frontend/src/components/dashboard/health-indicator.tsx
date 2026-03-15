"use client";

import Link from "next/link";
import { CheckCircle2, AlertTriangle, XCircle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { useHealthStatus, useAgentStatus, useDashboardStats } from "@/hooks/use-dashboard";
import { api } from "@/lib/api";
import toast from "react-hot-toast";
import { useState } from "react";

function computeHealthScore(
  agentStatus: { gmail_valid?: boolean; is_paused?: boolean } | undefined,
  stats: { emails_today?: number; auto_replied_today?: number } | undefined
): { score: number; breakdown: { label: string; points: number; max: number }[] } {
  const breakdown = [
    {
      label: "Gmail connected",
      points: agentStatus?.gmail_valid ? 25 : 0,
      max: 25,
    },
    {
      label: "Agent active",
      points: agentStatus && !agentStatus.is_paused ? 25 : 0,
      max: 25,
    },
    {
      label: "Emails processed today",
      points: (stats?.emails_today ?? 0) > 0 ? 25 : 0,
      max: 25,
    },
    {
      label: "Auto-reply rate > 80%",
      points:
        (stats?.emails_today ?? 0) > 0 &&
        ((stats?.auto_replied_today ?? 0) / (stats?.emails_today ?? 1)) * 100 > 80
          ? 25
          : 0,
      max: 25,
    },
  ];
  const score = breakdown.reduce((sum, b) => sum + b.points, 0);
  return { score, breakdown };
}

function scoreColor(score: number): string {
  if (score >= 90) return "text-success";
  if (score >= 70) return "text-yellow-500";
  if (score >= 50) return "text-orange-500";
  return "text-danger";
}

function scoreBg(score: number): string {
  if (score >= 90) return "bg-success/10";
  if (score >= 70) return "bg-yellow-500/10";
  if (score >= 50) return "bg-orange-500/10";
  return "bg-danger/10";
}

function scoreStroke(score: number): string {
  if (score >= 90) return "stroke-success";
  if (score >= 70) return "stroke-yellow-500";
  if (score >= 50) return "stroke-orange-500";
  return "stroke-danger";
}

export function HealthIndicator() {
  const { data: health, mutate } = useHealthStatus();
  const { data: agentStatus } = useAgentStatus();
  const { data: stats } = useDashboardStats();
  const [restarting, setRestarting] = useState(false);

  const handleRestart = async () => {
    setRestarting(true);
    try {
      await api.post("/api/health/restart");
      toast.success("Agent restart initiated");
      mutate();
    } catch {
      toast.error("Failed to restart agent");
    }
    setRestarting(false);
  };

  const { score, breakdown } = computeHealthScore(agentStatus, stats);
  const circumference = 2 * Math.PI * 40;
  const offset = circumference - (score / 100) * circumference;

  // If there's a critical error from the health endpoint, show it
  if (health?.status === "error") {
    const issue = health.issues[0];
    return (
      <div className="flex items-center gap-2 rounded-lg bg-danger/10 px-3 py-1.5">
        <XCircle className="h-4 w-4 text-danger" />
        <span className="text-xs font-medium text-danger">
          {issue?.message || "Agent paused"}
        </span>
        {issue?.action_url ? (
          <Link
            href={issue.action_url}
            className="ml-1 text-xs font-semibold text-danger underline hover:no-underline"
          >
            {issue.action_label || "Reconnect"}
          </Link>
        ) : (
          <button
            onClick={handleRestart}
            disabled={restarting}
            className={cn(
              "ml-1 inline-flex items-center gap-1 text-xs font-semibold text-danger underline hover:no-underline",
              restarting && "opacity-50"
            )}
          >
            <RefreshCw className={cn("h-3 w-3", restarting && "animate-spin")} />
            Restart
          </button>
        )}
      </div>
    );
  }

  return (
    <div className={cn("rounded-lg px-4 py-3", scoreBg(score))}>
      <div className="flex items-center gap-4">
        {/* Circular score */}
        <div className="relative flex h-16 w-16 shrink-0 items-center justify-center">
          <svg className="h-16 w-16 -rotate-90" viewBox="0 0 100 100">
            <circle
              cx="50"
              cy="50"
              r="40"
              fill="none"
              strokeWidth="6"
              className="stroke-background-2"
            />
            <circle
              cx="50"
              cy="50"
              r="40"
              fill="none"
              strokeWidth="6"
              strokeLinecap="round"
              strokeDasharray={circumference}
              strokeDashoffset={offset}
              className={cn("transition-all duration-500", scoreStroke(score))}
            />
          </svg>
          <span className={cn("absolute text-lg font-bold", scoreColor(score))}>
            {score}
          </span>
        </div>

        {/* Breakdown */}
        <div className="flex-1">
          <p className={cn("text-sm font-semibold", scoreColor(score))}>
            Agent Health: {score}/100
          </p>
          <div className="mt-1 flex flex-wrap gap-x-4 gap-y-0.5">
            {breakdown.map((b) => (
              <span key={b.label} className="flex items-center gap-1 text-[11px] text-text-3">
                {b.points > 0 ? (
                  <CheckCircle2 className="h-3 w-3 text-success" />
                ) : (
                  <AlertTriangle className="h-3 w-3 text-text-4" />
                )}
                {b.label}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
