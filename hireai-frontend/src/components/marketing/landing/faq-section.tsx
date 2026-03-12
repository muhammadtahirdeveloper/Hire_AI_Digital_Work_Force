"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";
import { ScrollReveal } from "./scroll-reveal";

const faqs = [
  {
    question: "Is my Gmail data safe?",
    answer:
      "Yes. We use AES-128 encryption for all stored data, OAuth2 for Gmail access (we never see your password), rate limiting to prevent abuse, and comprehensive audit logs. Your data is never shared with third parties.",
  },
  {
    question: "Can I use a different Gmail than my signup email?",
    answer:
      "Yes. You can connect any Gmail account to your HireAI agent. The Gmail you connect for processing does not need to match your HireAI login email.",
  },
  {
    question: "What happens after my free trial?",
    answer:
      "You choose a plan that fits your needs. If you decide not to subscribe, your agent simply pauses — no data is deleted, and you can reactivate anytime.",
  },
  {
    question: "Can I cancel anytime?",
    answer:
      "Yes. All plans are billed monthly with no long-term contracts. You can cancel anytime from your dashboard, and your agent will remain active until the end of your billing period.",
  },
  {
    question: "What if I want custom features?",
    answer:
      "We'd love to hear from you. Contact us at hireaidigitalemployee@gmail.com and we'll work with you to build what you need.",
  },
];

function FAQItem({
  question,
  answer,
}: {
  question: string;
  answer: string;
}) {
  const [open, setOpen] = useState(false);

  return (
    <div className="border-b border-border">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center justify-between py-5 text-left"
      >
        <span className="text-sm font-medium text-text">{question}</span>
        <ChevronDown
          className={cn(
            "h-4 w-4 shrink-0 text-text-3 transition-transform",
            open && "rotate-180"
          )}
        />
      </button>
      <div
        className={cn(
          "grid transition-all duration-200",
          open ? "grid-rows-[1fr] pb-5" : "grid-rows-[0fr]"
        )}
      >
        <div className="overflow-hidden">
          <p className="text-sm leading-relaxed text-text-3">{answer}</p>
        </div>
      </div>
    </div>
  );
}

export function FAQSection() {
  return (
    <section className="border-t border-border bg-background-1 py-20">
      <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8">
        <ScrollReveal>
          <div className="text-center">
            <h2 className="text-3xl font-bold tracking-tight text-text sm:text-4xl">
              Frequently asked questions
            </h2>
          </div>
        </ScrollReveal>

        <ScrollReveal delay={0.1}>
          <div className="mt-12">
            {faqs.map((faq) => (
              <FAQItem
                key={faq.question}
                question={faq.question}
                answer={faq.answer}
              />
            ))}
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
