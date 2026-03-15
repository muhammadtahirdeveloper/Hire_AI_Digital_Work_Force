"use client";

import Link from "next/link";
import { ArrowRight, Sparkles, Rocket } from "lucide-react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";

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

          {/* Beta Badge - replaces fake social proof */}
          <motion.div
            className="mt-12 flex flex-col items-center gap-3 sm:flex-row sm:justify-center"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.4 }}
          >
            <div className="flex items-center gap-2 rounded-full border border-navy/20 bg-navy/5 px-4 py-2">
              <Rocket className="h-4 w-4 text-navy" />
              <p className="text-sm font-medium text-text-2">
                Early Bird Pricing Active — Save up to 70%
              </p>
              <Sparkles className="h-4 w-4 text-navy" />
            </div>
          </motion.div>
        </div>
      </div>
    </section>
  );
}
