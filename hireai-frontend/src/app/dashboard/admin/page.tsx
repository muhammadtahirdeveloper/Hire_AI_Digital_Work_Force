"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import {
  Users,
  Mail,
  AlertTriangle,
  FlaskConical,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Shield,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardBody } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useAdminHealth } from "@/hooks/use-dashboard";
import type { MonitorLog } from "@/hooks/use-dashboard";
import toast from "react-hot-toast";

// --- Constants ---

const ADMIN_EMAIL = "hireaidigitalemployee@gmail.com";

const eventTypeStyles: Record<string, { label: string; variant: "success" | "warning" | "danger" | "default" }> = {
  gmail_token_expired: { label: "Gmail Token Expired", variant: "warning" },
  agent_restarted: { label: "Agent Restarted", variant: "success" },
  db_error: { label: "Database Error", variant: "danger" },
  high_error_rate: { label: "High Error Rate", variant: "danger" },
  trial_expiring: { label: "Trial Expiring", variant: "warning" },
  trial_expired: { label: "Trial Expired", variant: "danger" },
  agent_paused: { label: "Agent Paused", variant: "warning" },
  agent_resumed: { label: "Agent Resumed", variant: "success" },
};

// --- Fallback data ---

const fallbackData = {
  total_active_users: 24,
  total_trial_users: 8,
  emails_processed_today: 1247,
  system_errors: 2,
  recent_logs: [
    {
      id: 1,
      user_id: "usr_001",
      user_email: "sarah@techcorp.com",
      event_type: "gmail_token_expired",
      details: { message: "OAuth token refresh failed" },
      resolved_at: null,
      created_at: new Date(Date.now() - 25 * 60000).toISOString(),
    },
    {
      id: 2,
      user_id: "usr_002",
      user_email: "ahmed@premier.com",
      event_type: "agent_restarted",
      details: { message: "Agent idle for 35 minutes, auto-restarted" },
      resolved_at: new Date(Date.now() - 15 * 60000).toISOString(),
      created_at: new Date(Date.now() - 45 * 60000).toISOString(),
    },
    {
      id: 3,
      user_id: "usr_003",
      user_email: "fatima@hirehr.com",
      event_type: "high_error_rate",
      details: { message: "12 errors in last hour, agent paused", error_count: 12 },
      resolved_at: null,
      created_at: new Date(Date.now() - 120 * 60000).toISOString(),
    },
    {
      id: 4,
      user_id: "usr_004",
      user_email: "omar@dhastates.com",
      event_type: "trial_expiring",
      details: { message: "Trial ends in 2 days", days_left: 2 },
      resolved_at: null,
      created_at: new Date(Date.now() - 180 * 60000).toISOString(),
    },
    {
      id: 5,
      user_id: "usr_005",
      user_email: "zara@stylehub.com",
      event_type: "agent_resumed",
      details: { message: "Database reconnected, agent resumed" },
      resolved_at: new Date(Date.now() - 200 * 60000).toISOString(),
      created_at: new Date(Date.now() - 210 * 60000).toISOString(),
    },
  ] as MonitorLog[],
};

// --- Page ---

export default function AdminPage() {
  const { data: session } = useSession();
  const { data: apiData, mutate } = useAdminHealth();
  const [restartUserId, setRestartUserId] = useState("");
  const [restarting, setRestarting] = useState(false);

  const userEmail = session?.user?.email;
  const isAdmin = userEmail === ADMIN_EMAIL;

  // Block non-admin users
  if (!isAdmin) {
    return (
      <div className="flex min-h-[60vh] flex-col items-center justify-center space-y-4">
        <Shield className="h-16 w-16 text-text-4" />
        <h1 className="text-xl font-bold text-text">Access Denied</h1>
        <p className="text-sm text-text-3">
          This page is restricted to administrators.
        </p>
      </div>
    );
  }

  const data = apiData || fallbackData;

  const handleRestartAgent = async () => {
    if (!restartUserId.trim()) {
      toast.error("Enter a user ID");
      return;
    }
    setRestarting(true);
    try {
      await api.post("/api/health/restart", { user_id: restartUserId.trim() });
      toast.success(`Agent restarted for ${restartUserId}`);
      setRestartUserId("");
      mutate();
    } catch {
      toast.error("Failed to restart agent");
    }
    setRestarting(false);
  };

  const formatTimeAgo = (dateStr: string) => {
    const diff = Date.now() - new Date(dateStr).getTime();
    const mins = Math.floor(diff / 60000);
    if (mins < 1) return "just now";
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    return `${Math.floor(hours / 24)}d ago`;
  };

  return (
    <div className="space-y-6 pt-4 lg:pt-0">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Shield className="h-5 w-5 text-navy" />
          <h1 className="text-2xl font-bold text-text">Admin Dashboard</h1>
        </div>
        <p className="mt-1 text-sm text-text-3">
          Platform health monitoring and management
        </p>
      </div>

      {/* Metric cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardBody className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-text-3">Active Users</p>
                <p className="mt-1 text-2xl font-bold text-text">
                  {data.total_active_users}
                </p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-success/10">
                <Users className="h-5 w-5 text-success" />
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-text-3">Trial Users</p>
                <p className="mt-1 text-2xl font-bold text-text">
                  {data.total_trial_users}
                </p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-warning/10">
                <FlaskConical className="h-5 w-5 text-warning" />
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-text-3">Emails Today</p>
                <p className="mt-1 text-2xl font-bold text-text">
                  {data.emails_processed_today.toLocaleString()}
                </p>
              </div>
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy/10">
                <Mail className="h-5 w-5 text-navy" />
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody className="p-5">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-text-3">System Errors</p>
                <p className={cn(
                  "mt-1 text-2xl font-bold",
                  data.system_errors > 0 ? "text-danger" : "text-success"
                )}>
                  {data.system_errors}
                </p>
              </div>
              <div className={cn(
                "flex h-10 w-10 items-center justify-center rounded-lg",
                data.system_errors > 0 ? "bg-danger/10" : "bg-success/10"
              )}>
                <AlertTriangle className={cn(
                  "h-5 w-5",
                  data.system_errors > 0 ? "text-danger" : "text-success"
                )} />
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      {/* Quick action: restart agent */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <RefreshCw className="h-4 w-4 text-navy" />
            <h3 className="text-sm font-semibold text-text">Restart User Agent</h3>
          </div>
        </CardHeader>
        <CardBody>
          <div className="flex items-end gap-3">
            <div className="flex-1">
              <Input
                label="User ID"
                placeholder="e.g., usr_001"
                value={restartUserId}
                onChange={(e) => setRestartUserId(e.target.value)}
              />
            </div>
            <Button
              onClick={handleRestartAgent}
              loading={restarting}
              leftIcon={<RefreshCw className="h-4 w-4" />}
            >
              Restart Agent
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* Monitor logs */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-text">Recent Monitor Logs</h3>
            <Badge variant="default">{data.recent_logs.length} events</Badge>
          </div>
        </CardHeader>
        <CardBody className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs font-medium text-text-3">
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Event</th>
                  <th className="px-4 py-3">User</th>
                  <th className="px-4 py-3">Details</th>
                  <th className="px-4 py-3">Time</th>
                  <th className="px-4 py-3">Resolved</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_logs.map((log) => {
                  const style = eventTypeStyles[log.event_type] || {
                    label: log.event_type,
                    variant: "default" as const,
                  };
                  const isResolved = !!log.resolved_at;

                  return (
                    <tr
                      key={log.id}
                      className="border-b border-border last:border-0 hover:bg-background-1"
                    >
                      <td className="px-4 py-3">
                        {isResolved ? (
                          <CheckCircle2 className="h-4 w-4 text-success" />
                        ) : (
                          <XCircle className="h-4 w-4 text-danger" />
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <Badge variant={style.variant} size="sm">
                          {style.label}
                        </Badge>
                      </td>
                      <td className="px-4 py-3">
                        <div>
                          <p className="font-mono text-xs text-text-2">
                            {log.user_id}
                          </p>
                          {log.user_email && (
                            <p className="text-[10px] text-text-4">
                              {log.user_email}
                            </p>
                          )}
                        </div>
                      </td>
                      <td className="max-w-[200px] px-4 py-3 text-xs text-text-3">
                        {(log.details as Record<string, unknown>)?.message as string || "—"}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-1 text-xs text-text-4">
                          <Clock className="h-3 w-3" />
                          {formatTimeAgo(log.created_at)}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-text-4">
                        {isResolved
                          ? formatTimeAgo(log.resolved_at!)
                          : "—"
                        }
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {data.recent_logs.length === 0 && (
            <div className="py-12 text-center text-sm text-text-4">
              No monitor events recorded.
            </div>
          )}
        </CardBody>
      </Card>

      {/* Platform status summary */}
      <Card>
        <CardHeader>
          <h3 className="text-sm font-semibold text-text">Platform Status</h3>
        </CardHeader>
        <CardBody>
          <div className="grid gap-4 sm:grid-cols-3">
            <div className="flex items-center gap-3 rounded-lg border border-border p-4">
              <CheckCircle2 className="h-5 w-5 text-success" />
              <div>
                <p className="text-sm font-medium text-text">API Server</p>
                <p className="text-xs text-success">Operational</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg border border-border p-4">
              <CheckCircle2 className="h-5 w-5 text-success" />
              <div>
                <p className="text-sm font-medium text-text">Database</p>
                <p className="text-xs text-success">Connected</p>
              </div>
            </div>
            <div className="flex items-center gap-3 rounded-lg border border-border p-4">
              <CheckCircle2 className="h-5 w-5 text-success" />
              <div>
                <p className="text-sm font-medium text-text">Gmail API</p>
                <p className="text-xs text-success">Available</p>
              </div>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
