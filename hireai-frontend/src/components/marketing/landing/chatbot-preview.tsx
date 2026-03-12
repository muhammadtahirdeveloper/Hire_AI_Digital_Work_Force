"use client";

import { ScrollReveal } from "./scroll-reveal";

const messages = [
  {
    role: "ai" as const,
    text: "Hi! How can I help you today?",
  },
  {
    role: "user" as const,
    text: "My agent stopped processing emails",
  },
  {
    role: "ai" as const,
    text: "Checking status... Gmail token expired. Click here to reconnect \u2014 done in 30 seconds \u2705",
  },
];

export function ChatbotPreview() {
  return (
    <section className="py-20">
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
        <div className="grid items-center gap-12 lg:grid-cols-2">
          {/* Left: Text */}
          <ScrollReveal>
            <h2 className="text-3xl font-bold tracking-tight text-text sm:text-4xl">
              Support that never sleeps
            </h2>
            <p className="mt-4 text-lg text-text-3">
              Our AI assistant is available 24/7 to help you troubleshoot,
              configure, and get the most out of HireAI.
            </p>
          </ScrollReveal>

          {/* Right: Chat mockup */}
          <ScrollReveal delay={0.1}>
            <div className="mx-auto max-w-sm overflow-hidden rounded-xl border border-border shadow-lg">
              {/* Header */}
              <div className="flex items-center gap-3 border-b border-border bg-background-1 px-4 py-3">
                <div className="flex h-8 w-8 items-center justify-center rounded-full bg-navy text-xs font-bold text-white">
                  H
                </div>
                <div>
                  <p className="text-sm font-medium text-text">HireAI Assistant</p>
                  <p className="text-[10px] text-text-4">
                    Powered by Claude &middot;{" "}
                    <span className="text-success">Online</span>
                  </p>
                </div>
              </div>

              {/* Messages */}
              <div className="space-y-3 bg-background p-4">
                {messages.map((msg, i) => (
                  <div
                    key={i}
                    className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[80%] rounded-xl px-3 py-2 text-sm ${
                        msg.role === "user"
                          ? "bg-navy text-white"
                          : "bg-background-2 text-text"
                      }`}
                    >
                      {msg.text}
                    </div>
                  </div>
                ))}
              </div>

              {/* Input bar */}
              <div className="border-t border-border bg-background-1 px-4 py-3">
                <div className="flex items-center rounded-lg border border-border bg-background px-3 py-2">
                  <span className="flex-1 text-xs text-text-4">
                    Type a message...
                  </span>
                  <div className="flex h-6 w-6 items-center justify-center rounded-md bg-navy text-white">
                    <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M12 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </div>
            </div>
          </ScrollReveal>
        </div>
      </div>
    </section>
  );
}
