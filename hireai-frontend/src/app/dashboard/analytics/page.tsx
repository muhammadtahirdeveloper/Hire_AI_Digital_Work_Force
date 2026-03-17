"use client";

import { useState } from "react";
import useSWR from "swr";
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  Legend,
  ReferenceLine,
} from "recharts";
import {
  Mail,
  Zap,
  Clock,
  AlertTriangle,
  Timer,
  Activity,
  Download,
  ArrowUpRight,
  ArrowDownRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardBody } from "@/components/ui/card";
import { CardSkeleton } from "@/components/shared/card-skeleton";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

// --- Types ---

interface AnalyticsData {
  total_processed: number;
  auto_reply_rate: number;
  avg_response_time: number;
  emails_escalated: number;
  time_saved_hours: number;
  agent_uptime: number;
  volume_chart: { date: string; total: number; auto_handled: number }[];
  category_breakdown: { name: string; value: number }[];
  action_distribution: { action: string; count: number; percentage: number }[];
  top_senders: {
    rank: number;
    sender: string;
    emails: number;
    auto_handled: number;
    category: string;
  }[];
  response_time_trend: { date: string; avg_time: number }[];
  weekly_comparison: {
    metric: string;
    this_week: number;
    last_week: number;
    change: number;
    unit: string;
  }[];
}

// --- Constants ---

const periods = [
  { label: "Today", value: "today" },
  { label: "This Week", value: "week" },
  { label: "This Month", value: "month" },
  { label: "Last 3 Months", value: "quarter" },
];

const PIE_COLORS = ["#1D4ED8", "#2563EB", "#3B82F6", "#60A5FA", "#93C5FD", "#BFDBFE"];

const actionColors: Record<string, string> = {
  "Auto Replied": "bg-success",
  "Draft Created": "bg-navy",
  Escalated: "bg-warning",
  Blocked: "bg-danger",
};

const fetcher = (url: string) => api.get(url).then((r) => r.data?.data ?? r.data);

// --- Fallback data for demo rendering ---

const fallbackData: AnalyticsData = {
  total_processed: 1284,
  auto_reply_rate: 78,
  avg_response_time: 1.2,
  emails_escalated: 23,
  time_saved_hours: 47,
  agent_uptime: 99.8,
  volume_chart: [
    { date: "Mon", total: 42, auto_handled: 35 },
    { date: "Tue", total: 58, auto_handled: 48 },
    { date: "Wed", total: 65, auto_handled: 52 },
    { date: "Thu", total: 47, auto_handled: 40 },
    { date: "Fri", total: 71, auto_handled: 60 },
    { date: "Sat", total: 23, auto_handled: 20 },
    { date: "Sun", total: 15, auto_handled: 12 },
  ],
  category_breakdown: [
    { name: "CV", value: 35 },
    { name: "Interview", value: 20 },
    { name: "Spam", value: 15 },
    { name: "General", value: 12 },
    { name: "Escalated", value: 8 },
    { name: "Other", value: 10 },
  ],
  action_distribution: [
    { action: "Auto Replied", count: 1002, percentage: 78 },
    { action: "Draft Created", count: 193, percentage: 15 },
    { action: "Escalated", count: 64, percentage: 5 },
    { action: "Blocked", count: 25, percentage: 2 },
  ],
  top_senders: [
    { rank: 1, sender: "recruiter@techco.com", emails: 45, auto_handled: 42, category: "CV" },
    { rank: 2, sender: "info@realestate.pk", emails: 38, auto_handled: 35, category: "Inquiry" },
    { rank: 3, sender: "support@shopify.com", emails: 32, auto_handled: 30, category: "Order" },
    { rank: 4, sender: "hr@megacorp.com", emails: 28, auto_handled: 25, category: "Interview" },
    { rank: 5, sender: "newsletter@tech.io", emails: 24, auto_handled: 0, category: "Spam" },
  ],
  response_time_trend: [
    { date: "Mon", avg_time: 1.8 },
    { date: "Tue", avg_time: 1.5 },
    { date: "Wed", avg_time: 1.2 },
    { date: "Thu", avg_time: 1.3 },
    { date: "Fri", avg_time: 1.0 },
    { date: "Sat", avg_time: 0.9 },
    { date: "Sun", avg_time: 0.8 },
  ],
  weekly_comparison: [
    { metric: "Total Emails", this_week: 321, last_week: 290, change: 10.7, unit: "" },
    { metric: "Auto-Reply Rate", this_week: 78, last_week: 72, change: 8.3, unit: "%" },
    { metric: "Avg Response", this_week: 1.2, last_week: 1.8, change: -33.3, unit: "m" },
    { metric: "Escalated", this_week: 8, last_week: 12, change: -33.3, unit: "" },
  ],
};

// --- Page ---

export default function AnalyticsPage() {
  const [period, setPeriod] = useState("week");

  const { data: apiData, isLoading } = useSWR<AnalyticsData>(
    `/api/analytics?period=${period}`,
    fetcher,
    { revalidateOnFocus: false }
  );

  const data = apiData || fallbackData;

  const metricCards = [
    { label: "Total Processed", value: (data.total_processed ?? 0).toLocaleString(), icon: Mail, color: "text-navy" },
    { label: "Auto-Reply Rate", value: `${data.auto_reply_rate ?? 0}%`, icon: Zap, color: "text-success" },
    { label: "Avg Response Time", value: `${data.avg_response_time ?? 0}m`, icon: Clock, color: "text-navy" },
    { label: "Emails Escalated", value: String(data.emails_escalated ?? 0), icon: AlertTriangle, color: "text-warning" },
    { label: "Time Saved", value: `~${data.time_saved_hours ?? 0}h`, icon: Timer, color: "text-success" },
    { label: "Agent Uptime", value: `${data.agent_uptime ?? 0}%`, icon: Activity, color: "text-navy" },
  ];

  const handleExport = () => {
    window.open(
      `${api.defaults.baseURL}/api/analytics/export?period=${period}&format=pdf`,
      "_blank"
    );
  };

  return (
    <div className="space-y-6 pt-4 lg:pt-0">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text">Analytics</h1>
          <p className="mt-1 text-sm text-text-3">
            Insights into your agent&apos;s performance
          </p>
        </div>
        {/* 9. EXPORT */}
        <Button
          variant="outline"
          size="sm"
          onClick={handleExport}
          leftIcon={<Download className="h-4 w-4" />}
        >
          Download Full Report
        </Button>
      </div>

      {/* 1. DATE RANGE TABS */}
      <div className="flex flex-wrap gap-1">
        {periods.map((p) => (
          <button
            key={p.value}
            onClick={() => setPeriod(p.value)}
            className={cn(
              "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
              period === p.value
                ? "bg-navy text-white"
                : "text-text-3 hover:bg-background-2"
            )}
          >
            {p.label}
          </button>
        ))}
      </div>

      {/* 2. KEY METRICS */}
      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 6 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {metricCards.map((m) => (
            <Card key={m.label} hover>
              <CardBody className="p-5">
                <div className="flex items-center justify-between">
                  <p className="text-sm text-text-3">{m.label}</p>
                  <m.icon className={cn("h-4 w-4", m.color)} />
                </div>
                <p className="mt-2 text-3xl font-bold text-text">{m.value}</p>
              </CardBody>
            </Card>
          ))}
        </div>
      )}

      {/* 3. EMAIL VOLUME CHART */}
      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold text-text">Email Volume</h2>
        </CardHeader>
        <CardBody>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={data.volume_chart ?? []} margin={{ top: 5, right: 10, bottom: 5, left: -20 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="date" tick={{ fontSize: 12, fill: "var(--text-3)" }} />
                <YAxis tick={{ fontSize: 12, fill: "var(--text-3)" }} />
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: "var(--bg)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                />
                <Legend wrapperStyle={{ fontSize: "12px" }} />
                <Line
                  type="monotone"
                  dataKey="total"
                  name="Total Received"
                  stroke="var(--border-2)"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
                <Line
                  type="monotone"
                  dataKey="auto_handled"
                  name="Auto-Handled"
                  stroke="var(--navy)"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardBody>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* 4. CATEGORY BREAKDOWN — Donut */}
        <Card>
          <CardHeader>
            <h2 className="text-base font-semibold text-text">
              Category Breakdown
            </h2>
          </CardHeader>
          <CardBody>
            <div className="flex items-center gap-4">
              <div className="h-52 w-52 shrink-0">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={data.category_breakdown}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {(data.category_breakdown ?? []).map((_, i) => (
                        <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                      ))}
                    </Pie>
                    <RechartsTooltip
                      contentStyle={{
                        backgroundColor: "var(--bg)",
                        border: "1px solid var(--border)",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-2">
                {(data.category_breakdown ?? []).map((cat, i) => {
                  const total = (data.category_breakdown ?? []).reduce((s, c) => s + (c.value ?? 0), 0);
                  const pct = total > 0 ? Math.round((cat.value / total) * 100) : 0;
                  return (
                    <div key={cat.name} className="flex items-center gap-2 text-sm">
                      <span
                        className="inline-block h-3 w-3 rounded-sm"
                        style={{ backgroundColor: PIE_COLORS[i % PIE_COLORS.length] }}
                      />
                      <span className="text-text-2">{cat.name}</span>
                      <span className="ml-auto font-medium text-text">{pct}%</span>
                    </div>
                  );
                })}
              </div>
            </div>
          </CardBody>
        </Card>

        {/* 5. ACTION DISTRIBUTION — Horizontal bars */}
        <Card>
          <CardHeader>
            <h2 className="text-base font-semibold text-text">
              Action Distribution
            </h2>
          </CardHeader>
          <CardBody>
            <div className="space-y-4">
              {(data.action_distribution ?? []).map((item) => (
                <div key={item.action}>
                  <div className="mb-1 flex items-center justify-between text-sm">
                    <span className="text-text-2">{item.action}</span>
                    <span className="font-medium text-text">
                      {item.percentage ?? 0}%
                    </span>
                  </div>
                  <div className="h-2.5 w-full rounded-full bg-background-2">
                    <div
                      className={cn(
                        "h-2.5 rounded-full transition-all",
                        actionColors[item.action] || "bg-navy"
                      )}
                      style={{ width: `${item.percentage ?? 0}%` }}
                    />
                  </div>
                  <p className="mt-0.5 text-xs text-text-4">
                    {(item.count ?? 0).toLocaleString()} emails
                  </p>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>
      </div>

      {/* 6. TOP SENDERS */}
      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold text-text">Top Senders</h2>
        </CardHeader>
        <CardBody className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs font-medium text-text-3">
                  <th className="px-4 py-3">Rank</th>
                  <th className="px-4 py-3">Sender</th>
                  <th className="px-4 py-3 text-right">Emails</th>
                  <th className="px-4 py-3 text-right">Auto-Handled</th>
                  <th className="px-4 py-3">Category</th>
                </tr>
              </thead>
              <tbody>
                {(data.top_senders ?? []).map((sender) => (
                  <tr
                    key={sender.rank}
                    className="border-b border-border last:border-0 hover:bg-background-1"
                  >
                    <td className="px-4 py-3 font-medium text-text-3">
                      #{sender.rank}
                    </td>
                    <td className="px-4 py-3 font-medium text-text">
                      {sender.sender}
                    </td>
                    <td className="px-4 py-3 text-right text-text-2">
                      {sender.emails}
                    </td>
                    <td className="px-4 py-3 text-right text-text-2">
                      {sender.auto_handled}
                    </td>
                    <td className="px-4 py-3 text-text-3">{sender.category}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardBody>
      </Card>

      {/* 7. RESPONSE TIME TREND — Area chart */}
      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold text-text">
            Response Time Trend
          </h2>
        </CardHeader>
        <CardBody>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart
                data={data.response_time_trend ?? []}
                margin={{ top: 5, right: 10, bottom: 5, left: -20 }}
              >
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
                <XAxis dataKey="date" tick={{ fontSize: 12, fill: "var(--text-3)" }} />
                <YAxis
                  tick={{ fontSize: 12, fill: "var(--text-3)" }}
                  tickFormatter={(v) => `${v}m`}
                />
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: "var(--bg)",
                    border: "1px solid var(--border)",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                  formatter={(value: number) => [`${value}m`, "Avg Time"]}
                />
                <ReferenceLine
                  y={2}
                  stroke="var(--danger)"
                  strokeDasharray="3 3"
                  label={{ value: "Goal: < 2m", position: "right", fontSize: 10, fill: "var(--danger)" }}
                />
                <Area
                  type="monotone"
                  dataKey="avg_time"
                  stroke="var(--navy)"
                  fill="var(--navy-light)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </CardBody>
      </Card>

      {/* 8. WEEKLY COMPARISON */}
      <Card>
        <CardHeader>
          <h2 className="text-base font-semibold text-text">
            Weekly Comparison
          </h2>
        </CardHeader>
        <CardBody>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {(data.weekly_comparison ?? []).map((item) => {
              const change = item.change ?? 0;
              const improved =
                item.metric === "Escalated" || item.metric === "Avg Response"
                  ? change < 0
                  : change > 0;
              return (
                <div
                  key={item.metric}
                  className="rounded-lg border border-border p-4"
                >
                  <p className="text-xs text-text-3">{item.metric}</p>
                  <div className="mt-2 flex items-end gap-3">
                    <div>
                      <p className="text-xs text-text-4">This week</p>
                      <p className="text-xl font-bold text-text">
                        {item.this_week ?? 0}
                        {item.unit ?? ""}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-text-4">Last week</p>
                      <p className="text-lg text-text-3">
                        {item.last_week ?? 0}
                        {item.unit ?? ""}
                      </p>
                    </div>
                  </div>
                  <p
                    className={cn(
                      "mt-2 flex items-center gap-1 text-xs font-medium",
                      improved ? "text-success" : "text-danger"
                    )}
                  >
                    {improved ? (
                      <ArrowUpRight className="h-3 w-3" />
                    ) : (
                      <ArrowDownRight className="h-3 w-3" />
                    )}
                    {Math.abs(change).toFixed(1)}%{" "}
                    {improved ? "improved" : "worse"}
                  </p>
                </div>
              );
            })}
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
