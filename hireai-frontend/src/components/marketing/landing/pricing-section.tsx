"use client";

import Link from "next/link";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollReveal } from "./scroll-reveal";
import { cn } from "@/lib/utils";

const plans = [
  {
    name: "Starter",
    price: 19,
    model: "gpt-4o-mini",
    featured: false,
    features: [
      "500 emails/month",
      "1 Gmail account",
      "Smart classification",
      "Auto reply drafts",
      "Basic analytics",
    ],
  },
  {
    name: "Professional",
    price: 49,
    model: "gpt-4o",
    featured: true,
    features: [
      "5,000 emails/month",
      "3 Gmail accounts",
      "All Starter features",
      "Custom rules engine",
      "WhatsApp escalation",
      "Priority support",
    ],
  },
  {
    name: "Enterprise",
    price: 99,
    model: "claude-sonnet",
    featured: false,
    features: [
      "Unlimited emails",
      "10 Gmail accounts",
      "All Professional features",
      "Advanced analytics",
      "Custom agent training",
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

                <h3 className="text-lg font-semibold text-text">
                  {plan.name}
                </h3>

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

                <Link href="/auth/signup" className="mt-8 block">
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
