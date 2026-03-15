"use client";

import useSWR from "swr";
import { api } from "@/lib/api";
import type { DashboardStats, AgentStatus } from "@/types";

const fetcher = (url: string) =>
  api.get(url).then((res) => res.data?.data ?? res.data);

const REFRESH_INTERVAL = 30_000; // 30 seconds

export interface RecentEmail {
  id: string;
  from: string;
  from_name: string;
  subject: string;
  category: string;
  action: "auto_replied" | "draft_created" | "escalated" | "blocked";
  timestamp: string;
  escalation_reason?: string;
}

export interface WeeklySummary {
  total_emails: number;
  total_emails_change: number;
  time_saved_hours: number;
  auto_reply_rate: number;
  top_category: string;
}

export interface DailyVolume {
  day: string;
  total: number;
  auto_handled: number;
}

export function useDashboardStats() {
  return useSWR<DashboardStats>("/api/dashboard/stats", fetcher, {
    refreshInterval: REFRESH_INTERVAL,
    revalidateOnFocus: true,
  });
}

export function useRecentEmails(limit = 10) {
  return useSWR<RecentEmail[]>(
    `/api/emails/recent?limit=${limit}`,
    fetcher,
    {
      refreshInterval: REFRESH_INTERVAL,
      revalidateOnFocus: true,
    }
  );
}

export function useAgentStatus() {
  return useSWR<AgentStatus>("/api/agent/status", fetcher, {
    refreshInterval: REFRESH_INTERVAL,
    revalidateOnFocus: true,
  });
}

export function useWeeklySummary() {
  return useSWR<WeeklySummary>("/api/dashboard/weekly-summary", fetcher, {
    refreshInterval: 60_000,
  });
}

export function useDailyVolume() {
  return useSWR<DailyVolume[]>("/api/dashboard/daily-volume", fetcher, {
    refreshInterval: 60_000,
  });
}

export function useEscalatedEmails() {
  return useSWR<RecentEmail[]>(
    "/api/emails/recent?action=escalated&limit=5",
    fetcher,
    {
      refreshInterval: REFRESH_INTERVAL,
    }
  );
}

// --- Health hooks ---

export interface HealthStatus {
  status: "healthy" | "warning" | "error";
  gmail_connected: boolean;
  agent_running: boolean;
  db_connected: boolean;
  last_processed_at: string | null;
  issues: HealthIssue[];
}

export interface HealthIssue {
  type: "gmail_token_expired" | "agent_paused" | "db_error" | "high_error_rate";
  message: string;
  action_url?: string;
  action_label?: string;
}

export interface MonitorLog {
  id: number;
  user_id: string;
  user_email?: string;
  event_type: string;
  details: Record<string, unknown>;
  resolved_at: string | null;
  created_at: string;
}

export interface AdminHealth {
  total_active_users: number;
  total_trial_users: number;
  emails_processed_today: number;
  system_errors: number;
  recent_logs: MonitorLog[];
}

export function useHealthStatus() {
  return useSWR<HealthStatus>("/api/health/user", fetcher, {
    refreshInterval: 60_000,
    revalidateOnFocus: true,
  });
}

export function useAdminHealth() {
  return useSWR<AdminHealth>("/api/admin/health", fetcher, {
    refreshInterval: 60_000,
    revalidateOnFocus: true,
  });
}
