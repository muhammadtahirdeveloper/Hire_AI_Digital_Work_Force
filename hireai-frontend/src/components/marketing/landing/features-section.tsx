"use client";

import {
  Bot,
  PenLine,
  Shield,
  Zap,
  BarChart3,
  Bell,
} from "lucide-react";
import { ScrollReveal } from "./scroll-reveal";

const features = [
  {
    icon: Bot,
    title: "Smart Classification",
    description:
      "AI automatically categorizes every incoming email by intent, urgency, and department — no manual rules needed.",
  },
  {
    icon: PenLine,
    title: "Auto Reply Drafts",
    description:
      "Generate context-aware reply drafts that match your tone and brand, ready to send or edit.",
  },
  {
    icon: Shield,
    title: "Enterprise Security",
    description:
      "AES-128 encryption, OAuth2 Gmail access, rate limiting, and audit logs keep your data safe.",
  },
  {
    icon: Zap,
    title: "Custom Rules Engine",
    description:
      "Define triggers, filters, and actions to automate workflows specific to your business.",
  },
  {
    icon: BarChart3,
    title: "Live Analytics",
    description:
      "Real-time dashboards show processing volume, response times, and classification accuracy.",
  },
  {
    icon: Bell,
    title: "WhatsApp Escalation",
    description:
      "Critical emails instantly escalated to WhatsApp so you never miss what matters most.",
  },
];

export function FeaturesSection() {
  return (
    <section id="features" className="py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <ScrollReveal>
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-text sm:text-4xl">
              Everything your inbox needs to run itself
            </h2>
          </div>
        </ScrollReveal>

        <div className="mt-16 grid gap-px rounded-xl border border-border bg-border sm:grid-cols-2 lg:grid-cols-3">
          {features.map((feature, i) => (
            <ScrollReveal key={feature.title} delay={i * 0.05}>
              <div className="flex flex-col gap-3 bg-background p-8">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy-light">
                  <feature.icon className="h-5 w-5 text-navy" />
                </div>
                <h3 className="text-base font-semibold text-text">
                  {feature.title}
                </h3>
                <p className="text-sm leading-relaxed text-text-3">
                  {feature.description}
                </p>
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  );
}
