"use client";

import { ScrollReveal } from "./scroll-reveal";
import { AnimatedCounter } from "./animated-counter";

const stats = [
  { value: 50000, suffix: "+", label: "Emails Processed" },
  { value: 4, suffix: "", label: "Specialized Agents" },
  { value: 4, suffix: "", label: "Industries" },
  { value: 99.9, suffix: "%", label: "Platform Uptime" },
];

export function StatsSection() {
  return (
    <section className="border-y border-border bg-background-1">
      <div className="mx-auto max-w-7xl px-4 py-12 sm:px-6 lg:px-8">
        <ScrollReveal>
          <div className="grid grid-cols-2 gap-8 md:grid-cols-4">
            {stats.map((stat) => (
              <div key={stat.label} className="text-center">
                <p className="text-3xl font-bold text-text sm:text-4xl">
                  {stat.value === 99.9 ? (
                    <span>99.9{stat.suffix}</span>
                  ) : (
                    <AnimatedCounter
                      target={stat.value}
                      suffix={stat.suffix}
                    />
                  )}
                </p>
                <p className="mt-1 text-sm text-text-3">{stat.label}</p>
              </div>
            ))}
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
