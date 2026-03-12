"use client";

import { ScrollReveal } from "./scroll-reveal";

const metrics = [
  { label: "Processed", value: "1,284", change: "+12%" },
  { label: "Auto Replied", value: "847", change: "+8%" },
  { label: "Escalated", value: "23", change: "-5%" },
  { label: "Avg Response", value: "1.2m", change: "-18%" },
];

const recentEmails = [
  { from: "Sarah K.", subject: "Re: Senior Dev Application", tag: "HR", tagColor: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400", time: "2m ago" },
  { from: "Ali R.", subject: "Property listing inquiry — DHA Phase 6", tag: "Real Estate", tagColor: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400", time: "5m ago" },
  { from: "Zara M.", subject: "Order #4821 — refund request", tag: "E-commerce", tagColor: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400", time: "8m ago" },
  { from: "John D.", subject: "Meeting reschedule request", tag: "General", tagColor: "bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400", time: "12m ago" },
];

const agents = [
  { name: "HR Agent", active: true },
  { name: "Real Estate", active: false },
  { name: "E-commerce", active: false },
  { name: "General", active: false },
];

export function DashboardPreview() {
  return (
    <section className="py-20">
      <div className="mx-auto max-w-6xl px-4 sm:px-6 lg:px-8">
        <ScrollReveal>
          {/* Browser frame */}
          <div className="overflow-hidden rounded-xl border border-border shadow-2xl shadow-navy/5">
            {/* Browser bar */}
            <div className="flex items-center gap-2 border-b border-border bg-background-1 px-4 py-3">
              <div className="flex gap-1.5">
                <div className="h-3 w-3 rounded-full bg-red-400" />
                <div className="h-3 w-3 rounded-full bg-yellow-400" />
                <div className="h-3 w-3 rounded-full bg-green-400" />
              </div>
              <div className="ml-4 flex-1">
                <div className="mx-auto max-w-sm rounded-md bg-background-2 px-3 py-1 text-center text-xs text-text-4">
                  app.hireai.com/dashboard
                </div>
              </div>
            </div>

            {/* Dashboard content */}
            <div className="flex bg-background">
              {/* Mini sidebar */}
              <div className="hidden w-48 shrink-0 border-r border-border bg-background-1 p-4 md:block">
                <div className="flex items-center gap-2 mb-6">
                  <div className="flex h-6 w-6 items-center justify-center rounded bg-navy text-[10px] font-bold text-white">H</div>
                  <span className="text-sm font-bold text-text">HireAI</span>
                </div>
                {["Overview", "Agent", "Emails", "Analytics", "Settings"].map((item, i) => (
                  <div
                    key={item}
                    className={`rounded-md px-3 py-1.5 text-xs mb-1 ${
                      i === 0
                        ? "bg-navy text-white font-medium"
                        : "text-text-3"
                    }`}
                  >
                    {item}
                  </div>
                ))}
              </div>

              {/* Main content */}
              <div className="flex-1 p-4 sm:p-6">
                {/* Metrics */}
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {metrics.map((m) => (
                    <div key={m.label} className="rounded-lg border border-border p-3">
                      <p className="text-xs text-text-3">{m.label}</p>
                      <p className="mt-1 text-lg font-bold text-text">{m.value}</p>
                      <p className={`text-xs ${m.change.startsWith("+") ? "text-success" : "text-navy"}`}>
                        {m.change}
                      </p>
                    </div>
                  ))}
                </div>

                <div className="mt-4 grid gap-4 md:grid-cols-3">
                  {/* Recent activity */}
                  <div className="md:col-span-2 rounded-lg border border-border p-4">
                    <p className="text-sm font-medium text-text mb-3">Recent Activity</p>
                    <div className="space-y-3">
                      {recentEmails.map((email) => (
                        <div key={email.subject} className="flex items-center gap-3">
                          <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-background-2 text-[10px] font-medium text-text-2">
                            {email.from.split(" ").map(w => w[0]).join("")}
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="truncate text-xs font-medium text-text">{email.subject}</p>
                            <p className="text-[10px] text-text-4">{email.from} &middot; {email.time}</p>
                          </div>
                          <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${email.tagColor}`}>
                            {email.tag}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Agent selector */}
                  <div className="rounded-lg border border-border p-4">
                    <p className="text-sm font-medium text-text mb-3">Agent</p>
                    <div className="space-y-2">
                      {agents.map((agent) => (
                        <div
                          key={agent.name}
                          className={`rounded-md px-3 py-2 text-xs ${
                            agent.active
                              ? "border border-navy bg-navy/5 text-navy font-medium"
                              : "border border-border text-text-3"
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            {agent.name}
                            {agent.active && (
                              <span className="flex h-1.5 w-1.5 rounded-full bg-green-500" />
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </ScrollReveal>
      </div>
    </section>
  );
}
