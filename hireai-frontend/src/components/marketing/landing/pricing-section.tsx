"use client";

import Link from "next/link";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollReveal } from "./scroll-reveal";
import { cn } from "@/lib/utils";

const plans = [
  {
    name: "Starter",
    price: 9,
    badge: "Best for Testing",
    model: "Groq Llama (Free)",
    featured: false,
    features: [
      "500 emails/month",
      "Free API (Groq) — HireAI managed",
      "Optional BYOK any provider",
      "1 Gmail account",
      "Smart classification",
      "Auto reply drafts",
      "Basic analytics",
    ],
  },
  {
    name: "Professional",
    price: 29,
    badge: "Most Popular",
    model: "Claude Haiku — HireAI managed",
    featured: true,
    features: [
      "5,000 emails/month",
      "Claude Haiku — HireAI managed",
      "Optional BYOK any provider",
      "All 4 agents",
      "Custom rules engine",
      "WhatsApp escalation",
      "Advanced analytics",
    ],
  },
  {
    name: "Enterprise",
    price: 59,
    byokPrice: 39,
    badge: "Full Control",
    model: "Any model — BYOK option",
    featured: false,
    features: [
      "Unlimited emails",
      "$59/mo (HireAI managed key)",
      "$39/mo with BYOK",
      "All Professional features",
      "Own database",
      "API access",
      "Dedicated support",
    ],
  },
];

export function PricingSection() {
  return (
    <section id="pricing" className="py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <ScrollReveal>
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-text sm:text-4xl">
              Simple, transparent pricing
            </h2>
          </div>
        </ScrollReveal>

        <div className="mt-16 grid gap-8 md:grid-cols-3">
          {plans.map((plan, i) => (
            <ScrollReveal key={plan.name} delay={i * 0.1}>
              <div
                className={cn(
                  "relative flex h-full flex-col rounded-xl border p-8",
                  plan.featured
                    ? "border-navy bg-background shadow-lg shadow-navy/10"
                    : "border-border bg-background"
                )}
              >
                {plan.featured && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-navy px-3 py-1 text-xs font-medium text-white">
                    Most Popular
                  </span>
                )}

                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-semibold text-text">
                    {plan.name}
                  </h3>
                  <span className="rounded-full bg-background-1 border border-border px-2.5 py-0.5 text-[10px] font-medium text-text-3">
                    {plan.badge}
                  </span>
                </div>

                <div className="mt-4 flex items-baseline gap-1">
                  <span className="text-4xl font-bold text-text">
                    ${plan.price}
                  </span>
                  <span className="text-sm text-text-3">/month</span>
                </div>

                <p className="mt-2 font-mono text-xs text-text-4">
                  {plan.model}
                </p>

                <ul className="mt-6 flex-1 space-y-3">
                  {plan.features.map((feature) => (
                    <li
                      key={feature}
                      className="flex items-start gap-2 text-sm text-text-2"
                    >
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                      {feature}
                    </li>
                  ))}
                </ul>

                <Link href="/signup" className="mt-8 block">
                  <Button
                    variant={plan.featured ? "primary" : "outline"}
                    className="w-full"
                  >
                    Get started
                  </Button>
                </Link>
              </div>
            </ScrollReveal>
          ))}
        </div>

        <ScrollReveal>
          <div className="mt-8 text-center">
            <Link
              href="/pricing"
              className="text-sm font-medium text-navy hover:underline"
            >
              See full pricing &rarr;
            </Link>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
