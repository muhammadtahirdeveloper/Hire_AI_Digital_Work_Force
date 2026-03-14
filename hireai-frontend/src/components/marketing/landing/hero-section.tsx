"use client";

import Link from "next/link";
import { ArrowRight } from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";

const avatars = [
  { initials: "SA", bg: "bg-navy" },
  { initials: "MK", bg: "bg-emerald-600" },
  { initials: "ZA", bg: "bg-amber-600" },
  { initials: "RH", bg: "bg-rose-600" },
];

export function HeroSection() {
  return (
    <section className="relative overflow-hidden">
      {/* Subtle navy radial glow */}
      <div className="pointer-events-none absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/4 h-[600px] w-[600px] rounded-full bg-navy/5 blur-3xl" />

      <div className="relative mx-auto max-w-7xl px-4 py-24 sm:px-6 sm:py-32 lg:px-8 lg:py-40">
        <div className="mx-auto max-w-3xl text-center">
          {/* Badge */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5 }}
          >
            <span className="inline-flex items-center gap-2 rounded-full border border-border bg-background-1 px-4 py-1.5 text-sm text-text-2">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-navy opacity-75" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-navy" />
              </span>
              Now in beta &middot; No credit card required
            </span>
          </motion.div>

          {/* Headline */}
          <motion.h1
            className="mt-8 text-4xl font-bold tracking-tight text-text sm:text-6xl lg:text-7xl"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.1 }}
          >
            Your inbox,
            <br />
            run by{" "}
            <span className="bg-gradient-to-r from-navy to-blue-400 bg-clip-text text-transparent">
              intelligent agents
            </span>
          </motion.h1>

          {/* Subtext */}
          <motion.p
            className="mx-auto mt-6 max-w-xl text-lg text-text-3"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.2 }}
          >
            AI agents that read, classify, and respond to your emails
            automatically — so you stay focused on work that matters.
          </motion.p>

          {/* CTA Buttons */}
          <motion.div
            className="mt-10 flex flex-col items-center gap-4 sm:flex-row sm:justify-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.3 }}
          >
            <Link href="/signup">
              <Button size="lg" rightIcon={<ArrowRight className="h-4 w-4" />}>
                Start 7-day free trial
              </Button>
            </Link>
            <Link href="#how-it-works">
              <Button variant="ghost" size="lg">
                See how it works
              </Button>
            </Link>
          </motion.div>

          {/* Social Proof */}
          <motion.div
            className="mt-12 flex flex-col items-center gap-3 sm:flex-row sm:justify-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <div className="flex -space-x-2">
              {avatars.map((a) => (
                <div
                  key={a.initials}
                  className={`flex h-8 w-8 items-center justify-center rounded-full border-2 border-background text-xs font-medium text-white ${a.bg}`}
                >
                  {a.initials}
                </div>
              ))}
            </div>
            <p className="text-sm text-text-3">
              Trusted by 50+ businesses across 4 industries
            </p>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
