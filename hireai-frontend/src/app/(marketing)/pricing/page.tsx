"use client";

import { useState } from "react";
import Link from "next/link";
import { Check, X, ChevronDown, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody } from "@/components/ui/card";
import { cn } from "@/lib/utils";

// --- Plan data ---

const plans = [
  {
    id: "starter",
    name: "Starter",
    price: 9,
    badge: "Best for Testing",
    model: "Groq Llama (Free)",
    tagline: "Free API models with optional BYOK",
    popular: false,
    features: [
      { text: "500 emails per month", included: true },
      { text: "Free API (Groq) — HireAI managed", included: true },
      { text: "Optional BYOK any provider", included: true },
      { text: "1 agent (your choice)", included: true },
      { text: "Auto email classification", included: true },
      { text: "Reply draft creation", included: true },
      { text: "Basic analytics dashboard", included: true },
      { text: "Email support", included: true },
      { text: "Multiple Gmail accounts", included: false },
      { text: "WhatsApp alerts", included: false },
      { text: "Custom rules engine", included: false },
      { text: "Own database", included: false },
    ],
  },
  {
    id: "professional",
    name: "Professional",
    price: 29,
    badge: "Most Popular",
    model: "Claude Haiku — HireAI managed",
    tagline: "Best for growing businesses",
    popular: true,
    features: [
      { text: "5,000 emails per month", included: true },
      { text: "Claude Haiku — HireAI managed", included: true },
      { text: "Optional BYOK any provider", included: true },
      { text: "All 4 agents (switch anytime)", included: true },
      { text: "Auto-send replies (with approval)", included: true },
      { text: "Advanced analytics + charts", included: true },
      { text: "Custom rules engine", included: true },
      { text: "WhatsApp escalation alerts", included: true },
      { text: "2 Gmail accounts", included: true },
      { text: "Priority email support", included: true },
      { text: "Team members", included: false },
      { text: "Own database", included: false },
      { text: "API access", included: false },
    ],
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: 59,
    byokPrice: 39,
    badge: "Full Control",
    model: "Any model — BYOK option",
    tagline: "$59/mo managed or $39/mo with BYOK",
    popular: false,
    features: [
      { text: "Everything in Professional", included: true },
      { text: "$59/mo (HireAI managed key)", included: true },
      { text: "$39/mo with your own API key (BYOK)", included: true },
      { text: "Unlimited emails", included: true },
      { text: "Unlimited Gmail accounts", included: true },
      { text: "Team members (up to 5)", included: true },
      { text: "Connect own database", included: true },
      { text: "API access", included: true },
      { text: "Dedicated support", included: true },
    ],
  },
];

// --- Comparison table ---

const comparisonFeatures = [
  { feature: "Monthly emails", starter: "500", professional: "5,000", enterprise: "Unlimited" },
  { feature: "Gmail accounts", starter: "1", professional: "2", enterprise: "Unlimited" },
  { feature: "Agent types", starter: "1", professional: "All 4", enterprise: "All 4" },
  { feature: "AI model", starter: "Groq Llama (Free)", professional: "Claude Haiku", enterprise: "Any (BYOK)" },
  { feature: "BYOK option", starter: true, professional: true, enterprise: true },
  { feature: "Email classification", starter: true, professional: true, enterprise: true },
  { feature: "Reply drafts", starter: true, professional: true, enterprise: true },
  { feature: "Auto-send replies", starter: false, professional: true, enterprise: true },
  { feature: "Analytics dashboard", starter: "Basic", professional: "Advanced", enterprise: "Advanced" },
  { feature: "Custom rules engine", starter: false, professional: true, enterprise: true },
  { feature: "WhatsApp alerts", starter: false, professional: true, enterprise: true },
  { feature: "Working hours config", starter: false, professional: true, enterprise: true },
  { feature: "Team members", starter: false, professional: false, enterprise: "Up to 5" },
  { feature: "Own database", starter: false, professional: false, enterprise: true },
  { feature: "API access", starter: false, professional: false, enterprise: true },
  { feature: "Support", starter: "Email", professional: "Priority", enterprise: "Dedicated" },
  { feature: "Price", starter: "$9/mo", professional: "$29/mo", enterprise: "$59/$39/mo" },
];

// --- FAQ ---

const faqs = [
  {
    q: "When does my trial end?",
    a: "Your free trial lasts 7 days from the date you sign up. You'll receive a reminder email 2 days before it ends. No credit card is required to start.",
  },
  {
    q: "What is BYOK (Bring Your Own Key)?",
    a: "BYOK lets you use your own API key from providers like OpenAI, Claude, or Groq. Your key is encrypted and never shared. Enterprise BYOK pricing is $39/mo instead of $59/mo.",
  },
  {
    q: "What are the free API models?",
    a: "The Starter plan includes Groq Llama models at no extra cost — managed by HireAI. These models may produce less accurate results than Claude or GPT-4 but are great for testing.",
  },
  {
    q: "Can I switch plans?",
    a: "Yes, you can upgrade or downgrade your plan anytime. Changes take effect immediately. When downgrading, you retain access until the end of your current billing period.",
  },
  {
    q: "Do you offer refunds?",
    a: "We offer a full refund within the first 7 days of any paid plan. After that, you can cancel anytime but won't receive a refund for the current period.",
  },
  {
    q: "Is there a discount for annual payment?",
    a: "Annual billing with 2 months free is coming soon. Sign up for our newsletter to be notified when it's available.",
  },
];

// --- Page ---

export default function PricingPage() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
      {/* 1. Hero */}
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight text-text sm:text-4xl lg:text-5xl">
          Simple, transparent pricing
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-text-3">
          Start free for 7 days. No credit card. Cancel anytime.
        </p>

        {/* Monthly/Annual toggle */}
        <div className="mt-6 inline-flex items-center gap-3 rounded-full border border-border bg-background-1 px-4 py-2">
          <span className="text-sm font-medium text-text">Monthly</span>
          <button
            disabled
            className="relative h-5 w-9 cursor-not-allowed rounded-full bg-border-2"
            aria-label="Toggle annual billing (coming soon)"
          >
            <span className="absolute left-0.5 top-0.5 h-4 w-4 rounded-full bg-white transition-transform" />
          </button>
          <span className="text-sm text-text-4">
            Annual <span className="text-xs">(coming soon)</span>
          </span>
        </div>
      </div>

      {/* 2. Free trial highlight */}
      <div className="mt-12 rounded-2xl border-2 border-navy/30 bg-navy/5 p-6 text-center sm:p-8">
        <p className="text-lg font-bold text-text">
          Start with a 7-day FREE trial
        </p>
        <p className="mt-2 text-sm text-text-3">
          Full access to all features. No credit card required.
        </p>
        <Link href="/signup" className="mt-4 inline-block">
          <Button size="lg">
            Start Free Trial &rarr;
          </Button>
        </Link>
      </div>

      {/* 3. Pricing cards */}
      <div className="mt-16 grid gap-6 lg:grid-cols-3">
        {plans.map((plan) => (
          <Card
            key={plan.id}
            className={cn(
              "relative",
              plan.popular && "border-2 border-navy shadow-lg"
            )}
          >
            {plan.popular && (
              <Badge
                variant="navy"
                className="absolute -top-3 left-1/2 -translate-x-1/2"
              >
                Most Popular
              </Badge>
            )}
            <CardBody className="p-6">
              <div className="flex items-center justify-between">
                <p className="text-lg font-bold text-text">{plan.name}</p>
                <span className="rounded-full bg-background-1 border border-border px-2 py-0.5 text-[10px] font-medium text-text-3">
                  {plan.badge}
                </span>
              </div>
              <p className="mt-1 text-sm text-text-3">{plan.tagline}</p>

              <div className="mt-4">
                <span className="text-4xl font-bold text-text">${plan.price}</span>
                <span className="text-sm text-text-3">/month</span>
              </div>

              <p className="mt-2 font-mono text-xs text-text-4">{plan.model}</p>

              <Link href="/signup" className="mt-6 block">
                <Button
                  className="w-full"
                  variant={plan.popular ? "primary" : "outline"}
                >
                  Get Started
                </Button>
              </Link>

              <ul className="mt-6 space-y-2.5">
                {plan.features.map((f) => (
                  <li
                    key={f.text}
                    className={cn(
                      "flex items-start gap-2 text-sm",
                      f.included ? "text-text-2" : "text-text-4"
                    )}
                  >
                    {f.included ? (
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                    ) : (
                      <X className="mt-0.5 h-4 w-4 shrink-0 text-text-4" />
                    )}
                    {f.text}
                  </li>
                ))}
              </ul>
            </CardBody>
          </Card>
        ))}
      </div>

      {/* 4. Feature comparison table */}
      <div className="mt-20">
        <h2 className="text-center text-2xl font-bold text-text">
          Feature Comparison
        </h2>
        <p className="mt-2 text-center text-sm text-text-3">
          See exactly what you get with each plan
        </p>

        <div className="mt-8 overflow-x-auto rounded-xl border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="sticky top-0 border-b border-border bg-background-1">
                <th className="px-4 py-3 text-left text-xs font-semibold text-text-3">
                  Feature
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-text-3">
                  Starter ($9)
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-navy">
                  Professional ($29)
                </th>
                <th className="px-4 py-3 text-center text-xs font-semibold text-text-3">
                  Enterprise ($59/$39)
                </th>
              </tr>
            </thead>
            <tbody>
              {comparisonFeatures.map((row) => (
                <tr
                  key={row.feature}
                  className="border-b border-border last:border-0 hover:bg-background-1"
                >
                  <td className="px-4 py-3 font-medium text-text">
                    {row.feature}
                  </td>
                  {(["starter", "professional", "enterprise"] as const).map(
                    (plan) => {
                      const val = row[plan];
                      return (
                        <td key={plan} className="px-4 py-3 text-center">
                          {val === true ? (
                            <Check className="mx-auto h-4 w-4 text-success" />
                          ) : val === false ? (
                            <X className="mx-auto h-4 w-4 text-text-4" />
                          ) : (
                            <span className="text-sm text-text-2">{val}</span>
                          )}
                        </td>
                      );
                    }
                  )}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 5. FAQ */}
      <div className="mt-20">
        <h2 className="text-center text-2xl font-bold text-text">
          Frequently Asked Questions
        </h2>

        <div className="mx-auto mt-8 max-w-2xl space-y-3">
          {faqs.map((faq, i) => (
            <div
              key={i}
              className="rounded-lg border border-border"
            >
              <button
                onClick={() => setOpenFaq(openFaq === i ? null : i)}
                className="flex w-full items-center justify-between px-5 py-4 text-left"
              >
                <span className="text-sm font-medium text-text">{faq.q}</span>
                <ChevronDown
                  className={cn(
                    "h-4 w-4 shrink-0 text-text-4 transition-transform",
                    openFaq === i && "rotate-180"
                  )}
                />
              </button>
              {openFaq === i && (
                <div className="border-t border-border px-5 py-4 text-sm text-text-3">
                  {faq.a}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* 6. Contact */}
      <div className="mt-20 text-center">
        <h2 className="text-xl font-bold text-text">
          Questions about pricing?
        </h2>
        <p className="mt-2 text-sm text-text-3">
          We reply within 24 hours
        </p>
        <a
          href="mailto:hireaidigitalemployee@gmail.com"
          className="mt-4 inline-flex items-center gap-2 text-sm font-medium text-navy hover:underline"
        >
          <Mail className="h-4 w-4" />
          hireaidigitalemployee@gmail.com
        </a>
      </div>
    </div>
  );
}
