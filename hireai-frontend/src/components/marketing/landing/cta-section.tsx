"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { ScrollReveal } from "./scroll-reveal";

export function CTASection() {
  return (
    <section className="py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <ScrollReveal>
          <div className="relative overflow-hidden rounded-2xl bg-navy px-8 py-16 text-center sm:px-16">
            {/* Subtle glow */}
            <div className="pointer-events-none absolute -top-24 left-1/2 h-48 w-96 -translate-x-1/2 rounded-full bg-white/10 blur-3xl" />

            <h2 className="relative text-3xl font-bold tracking-tight text-white sm:text-4xl">
              Start free — see results today
            </h2>
            <p className="relative mx-auto mt-4 max-w-md text-base text-blue-100">
              7 days full access. All agents. Real emails. No credit card
              required.
            </p>
            <div className="relative mt-8">
              <Link href="/auth/signup">
                <Button
                  size="lg"
                  className="bg-white text-navy hover:bg-gray-100"
                  rightIcon={<ArrowRight className="h-4 w-4" />}
                >
                  Start your free trial
                </Button>
              </Link>
            </div>
            <p className="relative mt-4 text-xs text-blue-200">
              hireaidigitalemployee@gmail.com
            </p>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
