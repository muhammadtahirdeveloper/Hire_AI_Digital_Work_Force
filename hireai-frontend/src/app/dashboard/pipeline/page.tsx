"use client";

import { useState, useCallback } from "react";
import useSWR, { mutate } from "swr";
import {
  DollarSign,
  Plus,
  Trash2,
  ArrowRight,
  ArrowLeft,
  GripVertical,
  TrendingUp,
} from "lucide-react";
import { Card, CardBody } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardSkeleton } from "@/components/shared/card-skeleton";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

// --- Types ---

interface Deal {
  id: string;
  title: string;
  value: number;
  currency: string;
  stage: string;
  probability: number;
  contact_name: string | null;
  contact_email: string | null;
  expected_close_date: string | null;
  created_at: string;
  notes: string | null;
}

interface PipelineData {
  pipeline: Record<string, Deal[]>;
  total_value: number;
  total_deals: number;
}

// --- Constants ---

const STAGES = ["lead", "qualified", "proposal", "won", "lost"] as const;

const STAGE_LABELS: Record<string, string> = {
  lead: "Lead",
  qualified: "Qualified",
  proposal: "Proposal",
  won: "Won",
  lost: "Lost",
};

const STAGE_COLORS: Record<string, string> = {
  lead: "bg-blue-500",
  qualified: "bg-yellow-500",
  proposal: "bg-purple-500",
  won: "bg-green-500",
  lost: "bg-red-500",
};

const STAGE_BADGE: Record<string, "default" | "success" | "warning" | "danger" | "navy" | "outline"> = {
  lead: "navy",
  qualified: "warning",
  proposal: "outline",
  won: "success",
  lost: "danger",
};

const fetcher = (url: string) => api.get(url).then((r) => r.data?.data ?? r.data);

// --- Page ---

export default function PipelinePage() {
  const [showAdd, setShowAdd] = useState(false);
  const [newDeal, setNewDeal] = useState({ title: "", value: "", stage: "lead" });
  const [submitting, setSubmitting] = useState(false);

  const { data, isLoading } = useSWR<PipelineData>("/api/deals", fetcher, {
    revalidateOnFocus: false,
  });

  const pipeline = data?.pipeline ?? {};
  const totalValue = data?.total_value ?? 0;
  const totalDeals = data?.total_deals ?? 0;

  const moveDeal = useCallback(async (dealId: string, newStage: string) => {
    try {
      await api.patch(`/api/deals/${dealId}/stage`, { stage: newStage });
      mutate("/api/deals");
    } catch {
      // Silently fail — user will see deal hasn't moved
    }
  }, []);

  const deleteDeal = useCallback(async (dealId: string) => {
    if (!confirm("Delete this deal?")) return;
    try {
      await api.delete(`/api/deals/${dealId}`);
      mutate("/api/deals");
    } catch {
      // Silently fail
    }
  }, []);

  const addDeal = useCallback(async () => {
    if (!newDeal.title.trim()) return;
    setSubmitting(true);
    try {
      await api.post("/api/deals", {
        title: newDeal.title,
        value: parseFloat(newDeal.value) || 0,
        stage: newDeal.stage,
      });
      mutate("/api/deals");
      setNewDeal({ title: "", value: "", stage: "lead" });
      setShowAdd(false);
    } catch {
      // Silently fail
    } finally {
      setSubmitting(false);
    }
  }, [newDeal]);

  const stageIndex = (stage: string) => STAGES.indexOf(stage as typeof STAGES[number]);

  return (
    <div className="space-y-6 pt-4 lg:pt-0">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-text">Deal Pipeline</h1>
          <p className="mt-1 text-sm text-text-3">
            Track and manage your deals across stages
          </p>
        </div>
        <Button
          size="sm"
          leftIcon={<Plus className="h-4 w-4" />}
          onClick={() => setShowAdd(!showAdd)}
        >
          Add Deal
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid gap-4 sm:grid-cols-3">
        <Card hover>
          <CardBody className="p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm text-text-3">Total Pipeline Value</p>
              <DollarSign className="h-4 w-4 text-success" />
            </div>
            <p className="mt-2 text-3xl font-bold text-text">
              ${totalValue.toLocaleString()}
            </p>
          </CardBody>
        </Card>
        <Card hover>
          <CardBody className="p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm text-text-3">Active Deals</p>
              <TrendingUp className="h-4 w-4 text-navy" />
            </div>
            <p className="mt-2 text-3xl font-bold text-text">{totalDeals}</p>
          </CardBody>
        </Card>
        <Card hover>
          <CardBody className="p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm text-text-3">Won Value</p>
              <DollarSign className="h-4 w-4 text-success" />
            </div>
            <p className="mt-2 text-3xl font-bold text-success">
              ${(pipeline.won ?? []).reduce((s, d) => s + (d.value || 0), 0).toLocaleString()}
            </p>
          </CardBody>
        </Card>
      </div>

      {/* Add Deal Form */}
      {showAdd && (
        <Card>
          <CardBody className="p-5">
            <h3 className="mb-4 text-sm font-semibold text-text">New Deal</h3>
            <div className="grid gap-4 sm:grid-cols-3">
              <div>
                <label className="mb-1 block text-xs font-medium text-text-3">Title</label>
                <input
                  type="text"
                  value={newDeal.title}
                  onChange={(e) => setNewDeal({ ...newDeal, title: e.target.value })}
                  placeholder="Deal title"
                  className="w-full rounded-lg border border-border bg-background-1 px-3 py-2 text-sm text-text focus:border-navy focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-text-3">Value ($)</label>
                <input
                  type="number"
                  value={newDeal.value}
                  onChange={(e) => setNewDeal({ ...newDeal, value: e.target.value })}
                  placeholder="0.00"
                  className="w-full rounded-lg border border-border bg-background-1 px-3 py-2 text-sm text-text focus:border-navy focus:outline-none"
                />
              </div>
              <div>
                <label className="mb-1 block text-xs font-medium text-text-3">Stage</label>
                <select
                  value={newDeal.stage}
                  onChange={(e) => setNewDeal({ ...newDeal, stage: e.target.value })}
                  className="w-full rounded-lg border border-border bg-background-1 px-3 py-2 text-sm text-text focus:border-navy focus:outline-none"
                >
                  {STAGES.map((s) => (
                    <option key={s} value={s}>{STAGE_LABELS[s]}</option>
                  ))}
                </select>
              </div>
            </div>
            <div className="mt-4 flex gap-2">
              <Button size="sm" onClick={addDeal} loading={submitting}>
                Create Deal
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setShowAdd(false)}>
                Cancel
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {/* Kanban Board */}
      {isLoading ? (
        <div className="grid gap-4 lg:grid-cols-5">
          {Array.from({ length: 5 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-5">
          {STAGES.map((stage) => {
            const deals = pipeline[stage] ?? [];
            const stageValue = deals.reduce((s, d) => s + (d.value || 0), 0);

            return (
              <div key={stage} className="space-y-3">
                {/* Column Header */}
                <div className="flex items-center justify-between rounded-lg bg-background-2 px-3 py-2">
                  <div className="flex items-center gap-2">
                    <span className={cn("h-2.5 w-2.5 rounded-full", STAGE_COLORS[stage])} />
                    <span className="text-sm font-semibold text-text">
                      {STAGE_LABELS[stage]}
                    </span>
                    <Badge variant="default" size="sm">{deals.length}</Badge>
                  </div>
                  <span className="text-xs font-medium text-text-3">
                    ${stageValue.toLocaleString()}
                  </span>
                </div>

                {/* Deal Cards */}
                <div className="space-y-2 min-h-[100px]">
                  {deals.map((deal) => (
                    <Card key={deal.id} hover className="group">
                      <CardBody className="p-3">
                        <div className="flex items-start justify-between">
                          <div className="flex items-center gap-1.5 text-text-4">
                            <GripVertical className="h-3 w-3" />
                          </div>
                          <button
                            onClick={() => deleteDeal(deal.id)}
                            className="opacity-0 group-hover:opacity-100 transition-opacity"
                          >
                            <Trash2 className="h-3.5 w-3.5 text-text-4 hover:text-danger" />
                          </button>
                        </div>

                        <h4 className="mt-1 text-sm font-medium text-text line-clamp-2">
                          {deal.title}
                        </h4>

                        {deal.contact_name && (
                          <p className="mt-1 text-xs text-text-3 truncate">
                            {deal.contact_name}
                          </p>
                        )}

                        <div className="mt-2 flex items-center justify-between">
                          <span className="text-sm font-bold text-text">
                            ${(deal.value || 0).toLocaleString()}
                          </span>
                          <Badge variant={STAGE_BADGE[stage]} size="sm">
                            {deal.probability}%
                          </Badge>
                        </div>

                        {/* Stage Navigation */}
                        <div className="mt-2 flex items-center justify-between border-t border-border pt-2">
                          {stageIndex(stage) > 0 ? (
                            <button
                              onClick={() => moveDeal(deal.id, STAGES[stageIndex(stage) - 1])}
                              className="flex items-center gap-1 text-xs text-text-3 hover:text-text transition-colors"
                              title={`Move to ${STAGE_LABELS[STAGES[stageIndex(stage) - 1]]}`}
                            >
                              <ArrowLeft className="h-3 w-3" />
                              {STAGE_LABELS[STAGES[stageIndex(stage) - 1]]}
                            </button>
                          ) : (
                            <span />
                          )}
                          {stageIndex(stage) < STAGES.length - 1 ? (
                            <button
                              onClick={() => moveDeal(deal.id, STAGES[stageIndex(stage) + 1])}
                              className="flex items-center gap-1 text-xs text-text-3 hover:text-text transition-colors"
                              title={`Move to ${STAGE_LABELS[STAGES[stageIndex(stage) + 1]]}`}
                            >
                              {STAGE_LABELS[STAGES[stageIndex(stage) + 1]]}
                              <ArrowRight className="h-3 w-3" />
                            </button>
                          ) : (
                            <span />
                          )}
                        </div>
                      </CardBody>
                    </Card>
                  ))}

                  {deals.length === 0 && (
                    <div className="flex items-center justify-center rounded-lg border border-dashed border-border p-6">
                      <p className="text-xs text-text-4">No deals</p>
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
