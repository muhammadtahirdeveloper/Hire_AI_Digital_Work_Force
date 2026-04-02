"use client";

import { useState } from "react";
import useSWR from "swr";
import { Star, CheckCircle2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

// --- Types ---

interface Review {
  id: number;
  user_name: string;
  user_role?: string;
  user_company?: string;
  rating: number;
  review_text?: string;
  agent_type?: string;
  tier?: string;
  is_verified: boolean;
  created_at: string;
}

interface ReviewsData {
  reviews: Review[];
  average_rating: number;
  total_count: number;
  rating_breakdown: Record<number, number>;
}

// --- Empty defaults (only real reviews from API are shown) ---

const emptyData: ReviewsData = {
  average_rating: 0,
  total_count: 0,
  rating_breakdown: { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 },
  reviews: [],
};

const planFilters = ["All", "Starter", "Professional", "Enterprise"];
const agentFilters = ["All", "HR", "Real Estate", "E-commerce", "General"];

const planMap: Record<string, string> = { tier1: "Starter", tier2: "Professional", tier3: "Enterprise" };
const agentMap: Record<string, string> = { hr: "HR", real_estate: "Real Estate", ecommerce: "E-commerce", general: "General" };

const fetcher = (url: string) => api.get(url).then((r) => r.data);

// --- Page ---

export default function ReviewsPage() {
  const [planFilter, setPlanFilter] = useState("All");
  const [agentFilter, setAgentFilter] = useState("All");

  const { data: apiData } = useSWR<ReviewsData>(
    "/api/reviews/public",
    fetcher,
    { revalidateOnFocus: false }
  );

  const data = apiData || emptyData;
  const reviews = data?.reviews ?? emptyData.reviews;

  const filtered = reviews.filter((r) => {
    if (planFilter !== "All") {
      const rPlan = r.tier ? planMap[r.tier] : null;
      if (rPlan !== planFilter) return false;
    }
    if (agentFilter !== "All") {
      const rAgent = r.agent_type ? agentMap[r.agent_type] : null;
      if (rAgent !== agentFilter) return false;
    }
    return true;
  });

  const ratingBreakdown = data?.rating_breakdown ?? emptyData.rating_breakdown;
  const maxBreakdown = Math.max(...Object.values(ratingBreakdown), 1);

  return (
    <div className="mx-auto max-w-5xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight text-text sm:text-4xl">
          What our users say
        </h1>
        <p className="mt-2 text-text-3">
          Real reviews from real users
        </p>
      </div>

      {/* Overall Rating */}
      <div className="mt-12 grid gap-8 md:grid-cols-2">
        {/* Score */}
        <Card>
          <CardBody className="flex flex-col items-center justify-center p-8">
            <p className="text-6xl font-bold text-text">{data?.average_rating ?? emptyData.average_rating}</p>
            <div className="mt-2 flex gap-0.5">
              {[1, 2, 3, 4, 5].map((i) => (
                <Star
                  key={i}
                  className={cn(
                    "h-5 w-5",
                    i <= Math.round(data?.average_rating ?? emptyData.average_rating)
                      ? "fill-amber-400 text-amber-400"
                      : "text-border-2"
                  )}
                />
              ))}
            </div>
            <p className="mt-2 text-sm text-text-3">
              Based on {(data?.total_count ?? emptyData.total_count)} reviews
            </p>
          </CardBody>
        </Card>

        {/* Breakdown */}
        <Card>
          <CardBody className="space-y-3 p-8">
            {[5, 4, 3, 2, 1].map((star) => {
              const count = ratingBreakdown[star] || 0;
              const pct = (data?.total_count ?? emptyData.total_count) > 0 ? Math.round((count / (data?.total_count ?? emptyData.total_count)) * 100) : 0;
              return (
                <div key={star} className="flex items-center gap-3">
                  <span className="flex w-8 items-center gap-0.5 text-sm text-text-2">
                    {star} <Star className="h-3 w-3 fill-amber-400 text-amber-400" />
                  </span>
                  <div className="flex-1">
                    <div className="h-2.5 w-full rounded-full bg-background-2">
                      <div
                        className="h-2.5 rounded-full bg-amber-400 transition-all"
                        style={{ width: `${(count / maxBreakdown) * 100}%` }}
                      />
                    </div>
                  </div>
                  <span className="w-10 text-right text-xs text-text-4">
                    {pct}%
                  </span>
                </div>
              );
            })}
          </CardBody>
        </Card>
      </div>

      {/* Filters */}
      <div className="mt-10 flex flex-wrap items-center gap-4">
        <div>
          <span className="mr-2 text-xs text-text-3">Plan:</span>
          {planFilters.map((f) => (
            <button
              key={f}
              onClick={() => setPlanFilter(f)}
              className={cn(
                "mr-1 rounded-md px-3 py-1 text-xs font-medium transition-colors",
                planFilter === f
                  ? "bg-navy text-white"
                  : "text-text-3 hover:bg-background-2"
              )}
            >
              {f}
            </button>
          ))}
        </div>
        <div>
          <span className="mr-2 text-xs text-text-3">Agent:</span>
          {agentFilters.map((f) => (
            <button
              key={f}
              onClick={() => setAgentFilter(f)}
              className={cn(
                "mr-1 rounded-md px-3 py-1 text-xs font-medium transition-colors",
                agentFilter === f
                  ? "bg-navy text-white"
                  : "text-text-3 hover:bg-background-2"
              )}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      {/* Review Cards */}
      <div className="mt-8 grid gap-6 md:grid-cols-2">
        {filtered.map((review) => {
          const initials = review.user_name
            .split(" ")
            .map((w) => w[0])
            .join("")
            .slice(0, 2);

          return (
            <Card key={review.id}>
              <CardBody className="p-6">
                {/* Stars */}
                <div className="flex gap-0.5">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <Star
                      key={i}
                      className={cn(
                        "h-4 w-4",
                        i <= review.rating
                          ? "fill-amber-400 text-amber-400"
                          : "text-border-2"
                      )}
                    />
                  ))}
                </div>

                {/* Text */}
                {review.review_text && (
                  <p className="mt-3 text-sm leading-relaxed text-text-2">
                    &ldquo;{review.review_text}&rdquo;
                  </p>
                )}

                {/* Author */}
                <div className="mt-4 flex items-center gap-3 border-t border-border pt-4">
                  <div className="flex h-10 w-10 items-center justify-center rounded-full bg-navy text-sm font-medium text-white">
                    {initials}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <p className="text-sm font-medium text-text">
                        {review.user_name}
                      </p>
                      {review.is_verified && (
                        <CheckCircle2 className="h-3.5 w-3.5 text-navy" />
                      )}
                    </div>
                    <p className="text-xs text-text-4">
                      {[review.user_role, review.user_company]
                        .filter(Boolean)
                        .join(" at ")}
                    </p>
                  </div>
                </div>

                {/* Meta */}
                <div className="mt-3 flex flex-wrap items-center gap-2">
                  {review.agent_type && (
                    <Badge variant="navy" size="sm">
                      {agentMap[review.agent_type] || review.agent_type} Agent
                    </Badge>
                  )}
                  {review.tier && (
                    <Badge variant="outline" size="sm">
                      {planMap[review.tier] || review.tier}
                    </Badge>
                  )}
                  <span className="text-xs text-text-4">
                    {new Date(review.created_at).toLocaleDateString("en-US", {
                      month: "short",
                      day: "numeric",
                      year: "numeric",
                    })}
                  </span>
                  {review.is_verified && (
                    <Badge variant="success" size="sm">Verified User</Badge>
                  )}
                </div>
              </CardBody>
            </Card>
          );
        })}
      </div>

      {filtered.length === 0 && (
        <div className="mt-12 text-center">
          <p className="text-lg font-medium text-text-2">No reviews yet</p>
          <p className="mt-2 text-sm text-text-4">
            Be the first to share your experience with HireAI!
          </p>
        </div>
      )}
    </div>
  );
}
