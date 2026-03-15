"use client";

import { Rocket, Sparkles, Tag } from "lucide-react";
import { ScrollReveal } from "./scroll-reveal";

export function StatsSection() {
  return (
    <section className="border-y border-border bg-background-1">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <ScrollReveal>
          <div className="grid grid-cols-1 gap-6 md:grid-cols-3 text-center">
            <div className="flex flex-col items-center gap-2">
              <Rocket className="h-6 w-6 text-navy" />
              <p className="text-2xl font-bold text-text sm:text-3xl">
                Now in Beta
              </p>
              <p className="text-sm text-text-3">
                Early Bird Pricing Active
              </p>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Sparkles className="h-6 w-6 text-navy" />
              <p className="text-2xl font-bold text-text sm:text-3xl">
                Be Among Our First Users
              </p>
              <p className="text-sm text-text-3">
                Shape the product with your feedback
              </p>
            </div>
            <div className="flex flex-col items-center gap-2">
              <Tag className="h-6 w-6 text-navy" />
              <p className="text-2xl font-bold text-text sm:text-3xl">
                Save up to 70%
              </p>
              <p className="text-sm text-text-3">
                Limited time on all plans
              </p>
            </div>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
