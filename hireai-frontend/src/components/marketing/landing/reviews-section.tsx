"use client";

import Link from "next/link";
import { ArrowRight, Gift, Tag, MessageSquare } from "lucide-react";
import { ScrollReveal } from "./scroll-reveal";
import { Button } from "@/components/ui/button";

const cards = [
  {
    icon: Gift,
    title: "7-Day Free Trial",
    description: "Full access to all features. No credit card required. Cancel anytime.",
    color: "bg-navy/10 text-navy",
  },
  {
    icon: Tag,
    title: "Early Bird Pricing",
    description: "Lock in our lowest prices forever. Your rate never goes up as long as you stay.",
    color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400",
  },
  {
    icon: MessageSquare,
    title: "Shape the Product",
    description: "Your feedback directly influences our roadmap. Help us build what matters to you.",
    color: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400",
  },
];

export function ReviewsSection() {
  return (
    <section className="border-y border-border bg-background-1 py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <ScrollReveal>
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-text sm:text-4xl">
              Join Our Early Users
            </h2>
            <p className="mt-4 text-text-3">
              Be among our first users and shape the product
            </p>
          </div>
        </ScrollReveal>

        <div className="mt-16 grid gap-8 md:grid-cols-3">
          {cards.map((card, i) => (
            <ScrollReveal key={card.title} delay={i * 0.1}>
              <div className="flex h-full flex-col items-center rounded-xl border border-border bg-background p-8 text-center">
                <div className={`flex h-14 w-14 items-center justify-center rounded-2xl ${card.color}`}>
                  <card.icon className="h-7 w-7" />
                </div>
                <h3 className="mt-5 text-lg font-semibold text-text">
                  {card.title}
                </h3>
                <p className="mt-2 flex-1 text-sm leading-relaxed text-text-3">
                  {card.description}
                </p>
              </div>
            </ScrollReveal>
          ))}
        </div>

        <ScrollReveal>
          <div className="mt-12 text-center">
            <Link href="/signup">
              <Button size="lg" rightIcon={<ArrowRight className="h-4 w-4" />}>
                Start free trial
              </Button>
            </Link>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
