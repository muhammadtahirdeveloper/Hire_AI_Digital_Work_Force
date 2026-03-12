"use client";

import { Star } from "lucide-react";
import { ScrollReveal } from "./scroll-reveal";

const reviews = [
  {
    name: "Sarah Ahmed",
    role: "HR Manager",
    initials: "SA",
    bg: "bg-navy",
    review:
      "HireAI completely transformed how we handle recruitment emails. What used to take 3 hours now runs on autopilot. Our response rate to candidates improved by 85%.",
  },
  {
    name: "Mohammad Khan",
    role: "Real Estate Director",
    initials: "MK",
    bg: "bg-emerald-600",
    review:
      "Setup took 10 minutes. By next morning, 90% of property inquiries were handled automatically. Clients love the instant responses — and so do we.",
  },
  {
    name: "Zara Ali",
    role: "E-commerce Founder",
    initials: "ZA",
    bg: "bg-amber-600",
    review:
      "Response time went from 6 hours to 2 minutes. Our customer satisfaction scores jumped 40% in the first month. HireAI pays for itself many times over.",
  },
];

export function ReviewsSection() {
  return (
    <section className="border-y border-border bg-background-1 py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <ScrollReveal>
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="text-3xl font-bold tracking-tight text-text sm:text-4xl">
              What our users say
            </h2>
          </div>
        </ScrollReveal>

        <div className="mt-16 grid gap-8 md:grid-cols-3">
          {reviews.map((review, i) => (
            <ScrollReveal key={review.name} delay={i * 0.1}>
              <div className="flex h-full flex-col rounded-xl border border-border bg-background p-6">
                {/* Stars */}
                <div className="flex gap-0.5">
                  {Array.from({ length: 5 }).map((_, j) => (
                    <Star
                      key={j}
                      className="h-4 w-4 fill-amber-400 text-amber-400"
                    />
                  ))}
                </div>

                {/* Review text */}
                <p className="mt-4 flex-1 text-sm leading-relaxed text-text-2">
                  &ldquo;{review.review}&rdquo;
                </p>

                {/* Author */}
                <div className="mt-6 flex items-center gap-3 border-t border-border pt-4">
                  <div
                    className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-medium text-white ${review.bg}`}
                  >
                    {review.initials}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text">
                      {review.name}
                    </p>
                    <p className="text-xs text-text-3">{review.role}</p>
                  </div>
                </div>
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  );
}
