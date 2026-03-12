"use client";

import { useState, useCallback } from "react";
import useSWR from "swr";
import {
  Search,
  Download,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  Inbox,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody } from "@/components/ui/card";
import { TableSkeleton } from "@/components/shared/table-skeleton";
import { cn } from "@/lib/utils";
import { formatRelativeTime, truncate } from "@/lib/utils";
import { api } from "@/lib/api";

// --- Types ---

interface EmailEntry {
  id: string;
  from: string;
  from_name: string;
  from_email: string;
  subject: string;
  body: string;
  category: string;
  action: "auto_replied" | "draft_created" | "escalated" | "blocked";
  timestamp: string;
  confidence: number;
  agent_response?: string;
  actions_taken?: string[];
}

interface EmailsResponse {
  emails: EmailEntry[];
  total: number;
  page: number;
  pages: number;
}

// --- Constants ---

const dateRanges = [
  { label: "Today", value: "today" },
  { label: "This week", value: "week" },
  { label: "This month", value: "month" },
  { label: "All time", value: "all" },
];

const categories = [
  "All",
  "CV",
  "Interview",
  "Inquiry",
  "Spam",
  "Escalated",
  "Order",
  "General",
];

const actions = [
  { label: "All", value: "all" },
  { label: "Auto Replied", value: "auto_replied" },
  { label: "Draft Created", value: "draft_created" },
  { label: "Escalated", value: "escalated" },
  { label: "Blocked", value: "blocked" },
];

const actionBadgeMap: Record<string, { label: string; variant: "success" | "navy" | "warning" | "danger" }> = {
  auto_replied: { label: "Auto Replied", variant: "success" },
  draft_created: { label: "Draft Created", variant: "navy" },
  escalated: { label: "Escalated", variant: "warning" },
  blocked: { label: "Blocked", variant: "danger" },
};

const categoryColors: Record<string, string> = {
  CV: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400",
  Interview: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  Inquiry: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  Spam: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  Escalated: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  Order: "bg-orange-100 text-orange-700 dark:bg-orange-900/30 dark:text-orange-400",
  General: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400",
};

const PAGE_SIZE = 20;

const fetcher = (url: string) => api.get(url).then((r) => r.data);

// --- Page ---

export default function EmailLogPage() {
  const [search, setSearch] = useState("");
  const [dateRange, setDateRange] = useState("all");
  const [category, setCategory] = useState("All");
  const [action, setAction] = useState("all");
  const [page, setPage] = useState(1);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const queryParams = new URLSearchParams({
    page: String(page),
    limit: String(PAGE_SIZE),
    ...(search && { search }),
    ...(dateRange !== "all" && { period: dateRange }),
    ...(category !== "All" && { category }),
    ...(action !== "all" && { action }),
  });

  const { data, isLoading } = useSWR<EmailsResponse>(
    `/api/emails?${queryParams}`,
    fetcher,
    { revalidateOnFocus: false }
  );

  const emails = data?.emails || [];
  const total = data?.total || 0;
  const totalPages = data?.pages || 1;

  const handleExportCSV = useCallback(() => {
    const csvParams = new URLSearchParams({
      format: "csv",
      ...(search && { search }),
      ...(dateRange !== "all" && { period: dateRange }),
      ...(category !== "All" && { category }),
      ...(action !== "all" && { action }),
    });
    window.open(
      `${api.defaults.baseURL}/api/emails/export?${csvParams}`,
      "_blank"
    );
  }, [search, dateRange, category, action]);

  const startItem = (page - 1) * PAGE_SIZE + 1;
  const endItem = Math.min(page * PAGE_SIZE, total);

  return (
    <div className="space-y-6 pt-4 lg:pt-0">
      <div>
        <h1 className="text-2xl font-bold text-text">Email Log</h1>
        <p className="mt-1 text-sm text-text-3">
          All emails your agent has processed
        </p>
      </div>

      {/* 1. FILTERS BAR */}
      <Card>
        <CardBody className="p-4">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center">
            {/* Search */}
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-4" />
              <input
                type="text"
                placeholder="Search by sender or subject..."
                value={search}
                onChange={(e) => {
                  setSearch(e.target.value);
                  setPage(1);
                }}
                className="w-full rounded-lg border border-border bg-background py-2 pl-10 pr-3 text-sm text-text placeholder:text-text-4 focus:outline-none focus:ring-2 focus:ring-navy"
              />
            </div>

            {/* Date range */}
            <div className="flex flex-wrap gap-1">
              {dateRanges.map((d) => (
                <button
                  key={d.value}
                  onClick={() => {
                    setDateRange(d.value);
                    setPage(1);
                  }}
                  className={cn(
                    "rounded-md px-3 py-1.5 text-xs font-medium transition-colors",
                    dateRange === d.value
                      ? "bg-navy text-white"
                      : "text-text-3 hover:bg-background-2"
                  )}
                >
                  {d.label}
                </button>
              ))}
            </div>

            {/* Category */}
            <select
              value={category}
              onChange={(e) => {
                setCategory(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-border bg-background px-3 py-2 text-xs text-text focus:outline-none focus:ring-2 focus:ring-navy"
            >
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>

            {/* Action */}
            <select
              value={action}
              onChange={(e) => {
                setAction(e.target.value);
                setPage(1);
              }}
              className="rounded-lg border border-border bg-background px-3 py-2 text-xs text-text focus:outline-none focus:ring-2 focus:ring-navy"
            >
              {actions.map((a) => (
                <option key={a.value} value={a.value}>
                  {a.label}
                </option>
              ))}
            </select>

            {/* Export */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleExportCSV}
              leftIcon={<Download className="h-4 w-4" />}
            >
              Export CSV
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* 2. EMAIL TABLE */}
      <Card>
        <CardBody className="p-0">
          {isLoading ? (
            <div className="p-4">
              <TableSkeleton rows={8} />
            </div>
          ) : emails.length === 0 ? (
            /* 5. EMPTY STATE */
            <div className="flex flex-col items-center justify-center py-16 text-center">
              <Inbox className="mb-3 h-12 w-12 text-text-4" />
              <p className="text-sm font-medium text-text-2">
                No emails processed yet
              </p>
              <p className="mt-1 text-xs text-text-4">
                Your agent is watching your inbox.
              </p>
            </div>
          ) : (
            <>
              {/* Table Header */}
              <div className="hidden border-b border-border px-4 py-3 text-xs font-medium text-text-3 md:grid md:grid-cols-12 md:gap-4">
                <span className="col-span-1" />
                <span className="col-span-2">Sender</span>
                <span className="col-span-4">Subject</span>
                <span className="col-span-1">Category</span>
                <span className="col-span-2">Action</span>
                <span className="col-span-2">Time</span>
              </div>

              {/* Rows */}
              {emails.map((email) => {
                const badge = actionBadgeMap[email.action] || actionBadgeMap.blocked;
                const catColor = categoryColors[email.category] || categoryColors.General;
                const isExpanded = expandedId === email.id;
                const initials = email.from_name
                  ? email.from_name
                      .split(" ")
                      .map((w) => w[0])
                      .join("")
                      .slice(0, 2)
                  : "?";

                return (
                  <div key={email.id}>
                    <button
                      onClick={() =>
                        setExpandedId(isExpanded ? null : email.id)
                      }
                      className="w-full border-b border-border px-4 py-3 text-left transition-colors hover:bg-background-1 md:grid md:grid-cols-12 md:items-center md:gap-4"
                    >
                      {/* Avatar */}
                      <div className="col-span-1 hidden md:block">
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-background-2 text-xs font-medium text-text-2">
                          {initials}
                        </div>
                      </div>

                      {/* Sender */}
                      <div className="col-span-2">
                        <p className="text-sm font-medium text-text">
                          {email.from_name || email.from}
                        </p>
                        <p className="text-xs text-text-4">
                          {email.from_email || email.from}
                        </p>
                      </div>

                      {/* Subject */}
                      <div className="col-span-4 mt-1 md:mt-0">
                        <p className="text-sm text-text">
                          {truncate(email.subject, 60)}
                        </p>
                      </div>

                      {/* Category */}
                      <div className="col-span-1 mt-2 md:mt-0">
                        <span
                          className={cn(
                            "inline-flex rounded-full px-2 py-0.5 text-[10px] font-medium",
                            catColor
                          )}
                        >
                          {email.category}
                        </span>
                      </div>

                      {/* Action */}
                      <div className="col-span-2 mt-1 md:mt-0">
                        <Badge variant={badge.variant} size="sm">
                          {badge.label}
                        </Badge>
                      </div>

                      {/* Time + expand */}
                      <div className="col-span-2 mt-1 flex items-center justify-between md:mt-0">
                        <span className="text-xs text-text-4">
                          {formatRelativeTime(email.timestamp)}
                        </span>
                        {isExpanded ? (
                          <ChevronUp className="h-4 w-4 text-text-4" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-text-4" />
                        )}
                      </div>
                    </button>

                    {/* 3. EXPANDED ROW */}
                    {isExpanded && (
                      <div className="border-b border-border bg-background-1 px-6 py-5 space-y-4">
                        {/* Email body */}
                        <div>
                          <p className="mb-1 text-xs font-medium text-text-3">
                            Email Body
                          </p>
                          <div className="rounded-lg border border-border bg-background p-4 text-sm text-text-2 whitespace-pre-wrap">
                            {email.body || "No body content available."}
                          </div>
                        </div>

                        {/* Analysis */}
                        <div>
                          <p className="mb-1 text-xs font-medium text-text-3">
                            Agent Analysis
                          </p>
                          <p className="text-sm text-text-2">
                            Classified as:{" "}
                            <strong>{email.category}</strong> | Confidence:{" "}
                            <strong>{email.confidence || 95}%</strong>
                          </p>
                        </div>

                        {/* Agent response */}
                        {email.agent_response && (
                          <div>
                            <p className="mb-1 text-xs font-medium text-text-3">
                              Agent Response
                            </p>
                            <div className="rounded-lg border border-navy/20 bg-navy/5 p-4 text-sm text-text-2 whitespace-pre-wrap">
                              {email.agent_response}
                            </div>
                          </div>
                        )}

                        {/* Actions taken */}
                        {email.actions_taken && email.actions_taken.length > 0 && (
                          <div>
                            <p className="mb-1 text-xs font-medium text-text-3">
                              Actions Taken
                            </p>
                            <ul className="list-inside list-disc text-sm text-text-2">
                              {email.actions_taken.map((a, i) => (
                                <li key={i}>{a}</li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {/* Open in Gmail */}
                        <a
                          href={`https://mail.google.com/mail/u/0/#inbox/${email.id}`}
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          <Button
                            variant="outline"
                            size="sm"
                            leftIcon={<ExternalLink className="h-4 w-4" />}
                          >
                            Open in Gmail
                          </Button>
                        </a>
                      </div>
                    )}
                  </div>
                );
              })}
            </>
          )}
        </CardBody>
      </Card>

      {/* 4. PAGINATION */}
      {total > 0 && (
        <div className="flex items-center justify-between">
          <p className="text-xs text-text-4">
            Showing {startItem}–{endItem} of {total} emails
          </p>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="sm"
              disabled={page <= 1}
              onClick={() => setPage((p) => p - 1)}
            >
              Previous
            </Button>
            {Array.from({ length: Math.min(totalPages, 5) }).map((_, i) => {
              const pageNum = i + 1;
              return (
                <button
                  key={pageNum}
                  onClick={() => setPage(pageNum)}
                  className={cn(
                    "h-8 w-8 rounded-md text-xs font-medium transition-colors",
                    page === pageNum
                      ? "bg-navy text-white"
                      : "text-text-3 hover:bg-background-2"
                  )}
                >
                  {pageNum}
                </button>
              );
            })}
            {totalPages > 5 && (
              <span className="px-1 text-xs text-text-4">...</span>
            )}
            <Button
              variant="outline"
              size="sm"
              disabled={page >= totalPages}
              onClick={() => setPage((p) => p + 1)}
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
