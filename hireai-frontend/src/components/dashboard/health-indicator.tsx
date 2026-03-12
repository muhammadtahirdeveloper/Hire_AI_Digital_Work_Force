"use client";

import Link from "next/link";
import { CheckCircle2, AlertTriangle, XCircle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { useHealthStatus } from "@/hooks/use-dashboard";
import { api } from "@/lib/api";
import toast from "react-hot-toast";
import { useState } from "react";

export function HealthIndicator() {
  const { data: health, mutate } = useHealthStatus();
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

  // Default to healthy when API is unavailable
  if (!health) {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-success/10 px-3 py-1.5">
        <CheckCircle2 className="h-4 w-4 text-success" />
        <span className="text-xs font-medium text-success">All systems operational</span>
      </div>
    );
  }

  if (health.status === "healthy") {
    return (
      <div className="flex items-center gap-2 rounded-lg bg-success/10 px-3 py-1.5">
        <CheckCircle2 className="h-4 w-4 text-success" />
        <span className="text-xs font-medium text-success">All systems operational</span>
      </div>
    );
  }

  if (health.status === "warning") {
    const issue = health.issues[0];
    return (
      <div className="flex items-center gap-2 rounded-lg bg-warning/10 px-3 py-1.5">
        <AlertTriangle className="h-4 w-4 text-warning" />
        <span className="text-xs font-medium text-warning">
          {issue?.message || "Attention needed"}
        </span>
        {issue?.action_url && (
          <Link
            href={issue.action_url}
            className="ml-1 text-xs font-semibold text-warning underline hover:no-underline"
          >
            {issue.action_label || "Fix now"}
          </Link>
        )}
      </div>
    );
  }

  // Error state
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
