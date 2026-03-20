"use client";

import { useSession } from "next-auth/react";
import Link from "next/link";
import {
  Pause,
  Play,
  FlaskConical,
  RefreshCw,
  BarChart3,
  Mail,
  ArrowUpRight,
  ArrowDownRight,
  CheckCircle2,
  AlertTriangle,
  Bot,
  ExternalLink,
  X,
  Zap,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardBody } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { CardSkeleton } from "@/components/shared/card-skeleton";
import { cn } from "@/lib/utils";
import { formatRelativeTime } from "@/lib/utils";
import { api } from "@/lib/api";
import {
  useDashboardStats,
  useRecentEmails,
  useAgentStatus,
  useWeeklySummary,
  useDailyVolume,
  useEscalatedEmails,
} from "@/hooks/use-dashboard";
import { HealthIndicator } from "@/components/dashboard/health-indicator";
import toast from "react-hot-toast";
import { useState } from "react";

// --- Helpers ---

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

function getTrialDaysLeft(trialEndDate?: string): number {
  if (!trialEndDate) return 0;
  const diff = new Date(trialEndDate).getTime() - Date.now();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

function pctChange(current: number, previous: number): number {
  if (previous === 0) return current > 0 ? 100 : 0;
  return Math.round(((current - previous) / previous) * 100);
}

const actionStyles: Record<string, { label: string; color: string }> = {
  auto_replied: { label: "Auto replied", color: "text-success" },
  draft_created: { label: "Draft created", color: "text-navy" },
  escalated: { label: "Escalated", color: "text-warning" },
  blocked: { label: "Blocked", color: "text-danger" },
};

const categoryColors: Record<string, string> = {
  HR: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  CV: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
  Inquiry: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  Spam: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  Order: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  default: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400",
};

// --- Page ---

export default function DashboardOverviewPage() {
  const { data: session } = useSession();
  const { data: stats, isLoading: statsLoading } = useDashboardStats();
  const { data: recentEmails, isLoading: emailsLoading } = useRecentEmails();
  const { data: agentStatus, isLoading: agentLoading, mutate: mutateAgent } = useAgentStatus();
  const { data: weekly } = useWeeklySummary();
  const { data: dailyVolume } = useDailyVolume();
  const { data: escalated, mutate: mutateEscalated } = useEscalatedEmails();
  const [syncing, setSyncing] = useState(false);

  const user = session?.user;
  const isTrial = user?.tier === "trial";
  const trialDays = getTrialDaysLeft(user?.trialEndDate);
  const trialExpired = isTrial && trialDays === 0;

  const handleToggleAgent = async () => {
    try {
      const action = agentStatus?.is_paused ? "resume" : "pause";
      await api.post(`/api/agent/${action}`);
      mutateAgent();
      toast.success(`Agent ${action === "pause" ? "paused" : "resumed"}`);
    } catch {
      toast.error("Failed to update agent");
    }
  };

  const handleForceSync = async () => {
    setSyncing(true);
    try {
      await api.post("/api/agent/sync");
      toast.success("Sync triggered");
    } catch {
      toast.error("Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const handleTestModeToggle = async () => {
    try {
      await api.post("/api/agent/test-mode", {
        enabled: !agentStatus?.test_mode,
      });
      mutateAgent();
      toast.success(
        agentStatus?.test_mode ? "Test mode disabled" : "Test mode enabled"
      );
    } catch {
      toast.error("Failed to toggle test mode");
    }
  };

  const handleDismissEscalated = async (id: string) => {
    try {
      await api.post(`/api/emails/${id}/dismiss`);
      mutateEscalated();
    } catch {
      toast.error("Failed to dismiss");
    }
  };

  const emailsProcessed = stats?.emails_today ?? 0;
  const emailsYesterday = stats?.emails_yesterday ?? 0;
  const autoReplied = stats?.auto_replied_today ?? 0;
  const escalatedCount = stats?.escalated_today ?? 0;
  const avgResponse = stats?.avg_response_time ?? 0;
  const processedChange = pctChange(emailsProcessed, emailsYesterday);
  const autoReplyRate =
    emailsProcessed > 0 ? Math.round((autoReplied / emailsProcessed) * 100) : 0;

  return (
    <div className="space-y-6 pt-4 lg:pt-0">
      {/* 1. TOP HEADER */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text">
            {getGreeting()}, {user?.name?.split(" ")[0] || "there"}
          </h1>
          <p className="mt-1 text-sm text-text-3">
            Your agent processed {emailsProcessed} emails today
          </p>
        </div>
        <div className="flex items-center gap-2">
          {agentStatus && (
            <Badge variant={agentStatus.is_paused ? "warning" : "success"}>
              <span
                className={cn(
                  "mr-1.5 inline-block h-1.5 w-1.5 rounded-full",
                  agentStatus.is_paused ? "bg-warning" : "bg-success"
                )}
              />
              {agentStatus.is_paused ? "Paused" : "Live"}
            </Badge>
          )}
          {isTrial && !trialExpired && (
            <Badge variant="warning">Trial: {trialDays} days left</Badge>
          )}
          {!isTrial && user?.tier && (
            <Badge variant="navy" className="capitalize">
              {user.tier.replace("tier", "Tier ")}
            </Badge>
          )}
        </div>
      </div>

      {/* Health Indicator */}
      <HealthIndicator />

      {/* Trial expired banner */}
      {trialExpired && (
        <div className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="font-medium text-danger">
              Trial expired — choose a plan to continue
            </span>
            <Link href="/dashboard/billing">
              <Button size="sm" variant="danger">
                Choose Plan
              </Button>
            </Link>
          </div>
        </div>
      )}

      {/* 2. TRIAL BANNER */}
      {isTrial && !trialExpired && (
        <div className="rounded-lg border border-warning/30 bg-warning/10 px-4 py-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="text-text-2">
              Free Trial Active — <strong>{trialDays} days remaining</strong>.
              Upgrade anytime to keep your agent running.
            </span>
            <Link
              href="/dashboard/billing"
              className="shrink-0 font-medium text-navy hover:underline"
            >
              Upgrade Now &rarr;
            </Link>
          </div>
        </div>
      )}

      {/* Plan expiry warning */}
      {!isTrial && user?.trialEndDate && getTrialDaysLeft(user.trialEndDate) <= 7 && getTrialDaysLeft(user.trialEndDate) > 0 && (
        <div className="rounded-lg border border-warning/30 bg-warning/10 px-4 py-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="font-medium text-warning">
              <AlertTriangle className="mr-1.5 inline h-4 w-4" />
              Your plan expires in {getTrialDaysLeft(user.trialEndDate)} days
            </span>
            <Link href="/dashboard/billing">
              <Button size="sm">Renew Now</Button>
            </Link>
          </div>
        </div>
      )}

      {/* Gmail disconnected warning */}
      {agentStatus && !agentStatus.gmail_connected && (
        <div className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="font-medium text-danger">
              <AlertTriangle className="mr-1.5 inline h-4 w-4" />
              Gmail not connected. Connect your Gmail account to start processing emails.
            </span>
            <Link href="/dashboard/agent">
              <Button size="sm" variant="danger">Connect Gmail</Button>
            </Link>
          </div>
        </div>
      )}

      {/* Agent error / paused due to failures */}
      {agentStatus?.last_error && agentStatus.is_paused && (
        <div className="rounded-lg border border-warning/30 bg-warning/10 px-4 py-3 text-sm">
          <div className="flex items-center justify-between">
            <span className="font-medium text-warning">
              <AlertTriangle className="mr-1.5 inline h-4 w-4" />
              Agent paused due to errors. Check your settings and resume.
            </span>
            <Link href="/dashboard/agent">
              <Button size="sm">View & Resume</Button>
            </Link>
          </div>
        </div>
      )}

      {/* 3. QUICK ACTIONS */}
      <div className="flex flex-wrap items-center gap-3">
        <Button
          variant="outline"
          size="sm"
          onClick={handleToggleAgent}
          leftIcon={
            agentStatus?.is_paused ? (
              <Play className="h-4 w-4" />
            ) : (
              <Pause className="h-4 w-4" />
            )
          }
        >
          {agentStatus?.is_paused ? "Resume Agent" : "Pause Agent"}
        </Button>

        <div className="flex items-center gap-2 rounded-lg border border-border px-3 py-1.5">
          <FlaskConical className="h-4 w-4 text-text-3" />
          <Switch
            checked={agentStatus?.test_mode ?? false}
            onCheckedChange={handleTestModeToggle}
          />
          <span className="text-xs text-text-3">Test Mode</span>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={handleForceSync}
          loading={syncing}
          leftIcon={<RefreshCw className="h-4 w-4" />}
        >
          Force Sync
        </Button>

        <Link href="/dashboard/analytics">
          <Button
            variant="ghost"
            size="sm"
            leftIcon={<BarChart3 className="h-4 w-4" />}
          >
            View Full Analytics
          </Button>
        </Link>
      </div>

      {/* 4. METRICS CARDS */}
      {statsLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <Card hover>
            <CardBody className="p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm text-text-3">Total Processed</p>
                <Mail className="h-4 w-4 text-text-4" />
              </div>
              <p className="mt-2 text-3xl font-bold text-text">
                {emailsProcessed}
              </p>
              {processedChange !== 0 && (
                <p
                  className={cn(
                    "mt-1 flex items-center gap-1 text-xs",
                    processedChange > 0 ? "text-success" : "text-danger"
                  )}
                >
                  {processedChange > 0 ? (
                    <ArrowUpRight className="h-3 w-3" />
                  ) : (
                    <ArrowDownRight className="h-3 w-3" />
                  )}
                  {Math.abs(processedChange)}% vs yesterday
                </p>
              )}
            </CardBody>
          </Card>

          <Card hover>
            <CardBody className="p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm text-text-3">Auto Replied</p>
                <CheckCircle2 className="h-4 w-4 text-text-4" />
              </div>
              <p className="mt-2 text-3xl font-bold text-text">{autoReplied}</p>
              <p className="mt-1 text-xs text-text-4">
                {autoReplyRate}% reply rate
              </p>
            </CardBody>
          </Card>

          <Card hover>
            <CardBody className="p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm text-text-3">Escalated</p>
                <AlertTriangle className="h-4 w-4 text-text-4" />
              </div>
              <p className="mt-2 text-3xl font-bold text-text">
                {escalatedCount}
              </p>
              {escalatedCount > 0 && (
                <Link
                  href="#escalated"
                  className="mt-1 text-xs text-navy hover:underline"
                >
                  Needs your review
                </Link>
              )}
            </CardBody>
          </Card>

          <Card hover>
            <CardBody className="p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm text-text-3">Avg Response</p>
                <Zap className="h-4 w-4 text-text-4" />
              </div>
              <p className="mt-2 text-3xl font-bold text-text">
                {avgResponse.toFixed(1)}m
              </p>
              <p className="mt-1 flex items-center gap-1 text-xs text-success">
                <ArrowDownRight className="h-3 w-3" />
                Fast replies
              </p>
            </CardBody>
          </Card>
        </div>
      )}

      {/* USAGE METER */}
      {(() => {
        const tierLimits: Record<string, number> = { trial: 100, tier1: 500, tier2: 5000 };
        const limit = tierLimits[user?.tier || "trial"] ?? 0;
        const monthlyUsed = stats?.emails_this_month ?? emailsProcessed;
        const isUnlimited = user?.tier === "tier3";
        const pct = isUnlimited ? 0 : limit > 0 ? Math.min(100, Math.round((monthlyUsed / limit) * 100)) : 0;
        const isWarning = pct >= 80 && pct < 100;
        const isLimit = pct >= 100;

        return (
          <Card>
            <CardBody className="p-5">
              <div className="flex items-center justify-between">
                <p className="text-sm font-medium text-text">Emails this month</p>
                <p className="text-sm text-text-3">
                  {monthlyUsed}{isUnlimited ? " / Unlimited" : ` / ${limit.toLocaleString()}`}
                </p>
              </div>
              {!isUnlimited && (
                <div className="mt-2 h-2 w-full rounded-full bg-background-2">
                  <div
                    className={cn(
                      "h-2 rounded-full transition-all",
                      isLimit ? "bg-danger" : isWarning ? "bg-warning" : "bg-navy"
                    )}
                    style={{ width: `${pct}%` }}
                  />
                </div>
              )}
              {isWarning && (
                <p className="mt-2 flex items-center gap-1 text-xs text-warning">
                  <AlertTriangle className="h-3 w-3" />
                  Approaching limit — <Link href="/dashboard/billing" className="font-medium underline">upgrade plan</Link>
                </p>
              )}
              {isLimit && (
                <p className="mt-2 flex items-center gap-1 text-xs text-danger">
                  <AlertTriangle className="h-3 w-3" />
                  Limit reached — agent paused. <Link href="/dashboard/billing" className="font-medium underline">Upgrade now</Link>
                </p>
              )}
              {isUnlimited && (
                <p className="mt-2 text-xs text-success">Unlimited emails on your plan</p>
              )}
            </CardBody>
          </Card>
        );
      })()}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* 5. LIVE ACTIVITY FEED */}
        <div className="lg:col-span-2">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <h2 className="text-base font-semibold text-text">
                  Recent Activity
                </h2>
                <Link
                  href="/dashboard/emails"
                  className="text-xs text-navy hover:underline"
                >
                  View all &rarr;
                </Link>
              </div>
            </CardHeader>
            <CardBody>
              {emailsLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="flex items-center gap-3">
                      <div className="h-9 w-9 animate-pulse rounded-full bg-background-2" />
                      <div className="flex-1 space-y-1.5">
                        <div className="h-3 w-3/4 animate-pulse rounded bg-background-2" />
                        <div className="h-2.5 w-1/2 animate-pulse rounded bg-background-2" />
                      </div>
                    </div>
                  ))}
                </div>
              ) : recentEmails && recentEmails.length > 0 ? (
                <div className="space-y-1">
                  {recentEmails.map((email) => {
                    const style = actionStyles[email.action] || actionStyles.blocked;
                    const catColor =
                      categoryColors[email.category] || categoryColors.default;
                    const initials = email.from_name
                      ? email.from_name
                          .split(" ")
                          .map((w) => w[0])
                          .join("")
                          .slice(0, 2)
                      : email.from[0]?.toUpperCase() || "?";

                    return (
                      <div
                        key={email.id}
                        className="flex items-center gap-3 rounded-lg px-2 py-2.5 transition-colors hover:bg-background-1"
                      >
                        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-background-2 text-xs font-medium text-text-2">
                          {initials}
                        </div>
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium text-text">
                            {email.subject}
                          </p>
                          <p className="text-xs text-text-4">
                            {email.from_name || email.from} &middot;{" "}
                            <span className={style.color}>{style.label}</span>{" "}
                            &middot; {formatRelativeTime(email.timestamp)}
                          </p>
                        </div>
                        <span
                          className={cn(
                            "shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium",
                            catColor
                          )}
                        >
                          {email.category}
                        </span>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="py-8 text-center text-sm text-text-4">
                  No emails processed yet
                </div>
              )}
            </CardBody>
          </Card>
        </div>

        {/* 6. AGENT STATUS CARD */}
        <div>
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-navy" />
                <h2 className="text-base font-semibold text-text">
                  Agent Status
                </h2>
              </div>
            </CardHeader>
            <CardBody>
              {agentLoading ? (
                <div className="space-y-3">
                  {Array.from({ length: 5 }).map((_, i) => (
                    <div key={i} className="h-4 animate-pulse rounded bg-background-2" />
                  ))}
                </div>
              ) : agentStatus ? (
                <div className="space-y-3 text-sm">
                  <div className="flex justify-between">
                    <span className="text-text-3">Agent</span>
                    <span className="font-medium capitalize text-text">
                      {agentStatus.agent_type.replace("_", " ")}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-3">Tier</span>
                    <span className="font-medium capitalize text-text">
                      {agentStatus.tier}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-3">Model</span>
                    <span className="font-mono text-xs text-text-2">
                      {agentStatus.model}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-3">Gmail</span>
                    <span className="flex items-center gap-1 text-text-2">
                      {agentStatus.gmail_connected}
                      {agentStatus.gmail_valid ? (
                        <CheckCircle2 className="h-3 w-3 text-success" />
                      ) : (
                        <AlertTriangle className="h-3 w-3 text-warning" />
                      )}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-3">Last Processed</span>
                    <span className="flex items-center gap-1 text-text-2">
                      {agentStatus.last_processed ? (
                        <>
                          <span
                            className={cn(
                              "inline-block h-1.5 w-1.5 rounded-full",
                              (() => {
                                const diff = Date.now() - new Date(agentStatus.last_processed).getTime();
                                return diff < 600000 ? "bg-success" : diff < 1800000 ? "bg-warning" : "bg-danger";
                              })()
                            )}
                          />
                          {formatRelativeTime(agentStatus.last_processed)}
                        </>
                      ) : (
                        "Never"
                      )}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-3">Uptime</span>
                    <span className="text-text-2">
                      {stats?.agent_uptime_hours ?? 0}h
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-3">Queue</span>
                    <span className="text-text-2">
                      {stats?.emails_in_queue ?? 0}
                    </span>
                  </div>
                  <Link href="/dashboard/agent" className="block pt-2">
                    <Button variant="outline" size="sm" className="w-full">
                      Configure Agent &rarr;
                    </Button>
                  </Link>
                </div>
              ) : (
                <p className="text-sm text-text-4">Agent not configured</p>
              )}
            </CardBody>
          </Card>
        </div>
      </div>

      {/* 7. QUICK STATS CHART */}
      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold text-text">
            Email Volume — Last 7 Days
          </h2>
        </CardHeader>
        <CardBody>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart
                data={
                  dailyVolume || [
                    { day: "Mon", total: 42, auto_handled: 35 },
                    { day: "Tue", total: 58, auto_handled: 48 },
                    { day: "Wed", total: 65, auto_handled: 52 },
                    { day: "Thu", total: 47, auto_handled: 40 },
                    { day: "Fri", total: 71, auto_handled: 60 },
                    { day: "Sat", total: 23, auto_handled: 20 },
                    { day: "Sun", total: 15, auto_handled: 12 },
                  ]
                }
                margin={{ top: 5, right: 5, bottom: 5, left: -20 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="day" tick={{ fontSize: 12, fill: "var(--text-3)" }} />
                <YAxis tick={{ fontSize: 12, fill: "var(--text-3)" }} />
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: "var(--bg)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
                <Legend
                  wrapperStyle={{ fontSize: "12px" }}
                  formatter={(value) =>
                    value === "total" ? "Total Received" : "Auto-handled"
                  }
                />
                <Bar dataKey="total" fill="var(--border-2)" radius={[4, 4, 0, 0]} />
                <Bar dataKey="auto_handled" fill="var(--navy)" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </CardBody>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* 8. ESCALATED EMAILS */}
        <Card id="escalated">
          <CardHeader>
            <h2 className="text-base font-semibold text-text">
              <AlertTriangle className="mr-1.5 inline h-4 w-4 text-warning" />
              Needs Your Attention
              {escalated && escalated.length > 0 && (
                <span className="ml-1.5 text-text-3">({escalated.length})</span>
              )}
            </h2>
          </CardHeader>
          <CardBody>
            {escalated && escalated.length > 0 ? (
              <div className="space-y-3">
                {escalated.map((email) => (
                  <div
                    key={email.id}
                    className="flex items-start gap-3 rounded-lg border border-border p-3"
                  >
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-text">
                        {email.subject}
                      </p>
                      <p className="text-xs text-text-3">
                        {email.from_name || email.from}
                      </p>
                      {email.escalation_reason && (
                        <p className="mt-1 text-xs text-warning">
                          {email.escalation_reason}
                        </p>
                      )}
                    </div>
                    <div className="flex shrink-0 gap-1.5">
                      <a
                        href={`https://mail.google.com/mail/u/0/#inbox/${email.id}`}
                        target="_blank"
                        rel="noopener noreferrer"
                      >
                        <Button variant="outline" size="sm">
                          <ExternalLink className="h-3 w-3" />
                          Reply
                        </Button>
                      </a>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDismissEscalated(email.id)}
                      >
                        <X className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="py-6 text-center text-sm text-text-4">
                <CheckCircle2 className="mx-auto mb-2 h-8 w-8 text-success" />
                All clear! No emails need your attention.
              </div>
            )}
          </CardBody>
        </Card>

        {/* 9. WEEKLY SUMMARY */}
        <Card>
          <CardHeader>
            <h2 className="text-base font-semibold text-text">
              Weekly Summary
            </h2>
          </CardHeader>
          <CardBody>
            {weekly ? (
              <div className="grid grid-cols-2 gap-4">
                <div className="rounded-lg bg-background-1 p-4">
                  <p className="text-xs text-text-3">Total Emails</p>
                  <p className="mt-1 text-2xl font-bold text-text">
                    {weekly.total_emails}
                  </p>
                  <p
                    className={cn(
                      "text-xs",
                      weekly.total_emails_change >= 0
                        ? "text-success"
                        : "text-danger"
                    )}
                  >
                    {weekly.total_emails_change >= 0 ? "+" : ""}
                    {weekly.total_emails_change}% vs last week
                  </p>
                </div>
                <div className="rounded-lg bg-background-1 p-4">
                  <p className="text-xs text-text-3">Time Saved</p>
                  <p className="mt-1 text-2xl font-bold text-text">
                    ~{weekly.time_saved_hours}h
                  </p>
                  <p className="text-xs text-text-4">This week</p>
                </div>
                <div className="rounded-lg bg-background-1 p-4">
                  <p className="text-xs text-text-3">Auto-reply Rate</p>
                  <p className="mt-1 text-2xl font-bold text-text">
                    {weekly.auto_reply_rate}%
                  </p>
                  <p className="text-xs text-text-4">Automated</p>
                </div>
                <div className="rounded-lg bg-background-1 p-4">
                  <p className="text-xs text-text-3">Top Category</p>
                  <p className="mt-1 text-2xl font-bold text-text">
                    {weekly.top_category}
                  </p>
                  <p className="text-xs text-text-4">Most processed</p>
                </div>
              </div>
            ) : (
              <div className="grid grid-cols-2 gap-4">
                {Array.from({ length: 4 }).map((_, i) => (
                  <div key={i} className="rounded-lg bg-background-1 p-4">
                    <div className="h-3 w-16 animate-pulse rounded bg-background-2" />
                    <div className="mt-2 h-7 w-12 animate-pulse rounded bg-background-2" />
                    <div className="mt-1 h-2.5 w-20 animate-pulse rounded bg-background-2" />
                  </div>
                ))}
              </div>
            )}
          </CardBody>
        </Card>
      </div>

      {/* 10. UPGRADE PROMPT (tier1 only) */}
      {user?.tier === "tier1" && (
        <Card className="border-navy/20 bg-gradient-to-r from-navy/5 to-transparent">
          <CardBody className="p-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-start gap-3">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-navy-light">
                  <Zap className="h-5 w-5 text-navy" />
                </div>
                <div>
                  <p className="font-semibold text-text">
                    Unlock unlimited emails and all 4 agents
                  </p>
                  <p className="mt-0.5 text-sm text-text-3">
                    You&apos;re on the Starter plan (500 emails/month). Upgrade
                    to Professional for 5,000 emails and priority support.
                  </p>
                </div>
              </div>
              <Link href="/dashboard/billing" className="shrink-0">
                <Button size="sm">Upgrade to Pro &rarr;</Button>
              </Link>
            </div>
          </CardBody>
        </Card>
      )}
    </div>
  );
}
