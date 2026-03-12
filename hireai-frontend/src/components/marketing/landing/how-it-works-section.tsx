"use client";

import { ScrollReveal } from "./scroll-reveal";

const steps = [
  {
    number: "1",
    title: "Connect Gmail",
    description: "Link any Gmail account in 30 seconds",
  },
  {
    number: "2",
    title: "Choose Your Agent",
    description: "Select the agent that fits your industry",
  },
  {
    number: "3",
    title: "Go Live",
    description: "Watch your inbox run on autopilot",
  },
];

export function HowItWorksSection() {
  return (
    <section id="how-it-works" className="border-y border-border bg-background-1 py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <ScrollReveal>
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-text sm:text-4xl">
              Up and running in 3 steps
            </h2>
          </div>
        </ScrollReveal>

        <div className="relative mt-16">
          {/* Dashed connector line (desktop) */}
          <div className="absolute left-0 right-0 top-7 hidden h-px border-t-2 border-dashed border-border-2 lg:block" style={{ left: '16.67%', right: '16.67%' }} />

          <div className="grid gap-12 md:grid-cols-3">
            {steps.map((step, i) => (
              <ScrollReveal key={step.number} delay={i * 0.1}>
                <div className="relative flex flex-col items-center text-center">
                  <div className="relative z-10 flex h-14 w-14 items-center justify-center rounded-full bg-navy text-lg font-bold text-white shadow-lg shadow-navy/20">
                    {step.number}
                  </div>
                  <h3 className="mt-6 text-lg font-semibold text-text">
                    {step.title}
                  </h3>
                  <p className="mt-2 text-sm text-text-3">
                    {step.description}
                  </p>
                </div>
              </ScrollReveal>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
