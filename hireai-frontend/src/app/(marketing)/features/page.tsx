"use client";

import Link from "next/link";
import {
  Brain,
  MessageSquare,
  ShieldCheck,
  Users,
  Workflow,
  BarChart3,
  Smartphone,
  Lock,
  HeartPulse,
  Bot,
  Check,
  ArrowRight,
  Home,
  ShoppingCart,
  Briefcase,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardBody } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

// --- Feature sections data ---

const featureSections = [
  {
    id: "classification",
    icon: Brain,
    title: "Smart Email Classification",
    description:
      "Our AI reads every incoming email and instantly categorizes it — HR, sales inquiry, support request, spam, or any custom category you define.",
    details: [
      "Classifies emails in under 2 seconds",
      "Learns from your corrections over time",
      "Supports 15+ built-in categories",
      "Custom category training available",
    ],
  },
  {
    id: "replies",
    icon: MessageSquare,
    title: "AI Reply Generation",
    description:
      "Generate professional, context-aware replies that match your tone and business style. Review before sending or let the agent auto-send approved categories.",
    details: [
      "Context-aware responses using full email thread",
      "Matches your brand voice and style",
      "Draft mode or auto-send mode",
      "Supports multiple languages",
    ],
  },
  {
    id: "safety",
    icon: ShieldCheck,
    title: "Safety System",
    description:
      "Built-in guardrails ensure your AI agent never crosses boundaries. Every action is logged and auditable.",
    details: [
      "Never sends emails without approval (unless configured)",
      "Never shares sensitive data externally",
      "Never modifies or deletes emails",
      "Never accesses attachments without permission",
      "Never sends to external addresses not in context",
      "All actions logged with full audit trail",
    ],
  },
  {
    id: "agents",
    icon: Users,
    title: "Industry-Specific Agents",
    description:
      "Choose the agent that fits your business. Each is fine-tuned for specific industry email patterns and vocabulary.",
    agents: [
      {
        name: "General Agent",
        icon: Briefcase,
        handles: ["Email classification", "Smart replies", "Meeting scheduling", "Follow-ups"],
      },
      {
        name: "HR Agent",
        icon: Users,
        handles: ["CV screening", "Interview scheduling", "Candidate responses", "Application tracking"],
      },
      {
        name: "Real Estate Agent",
        icon: Home,
        handles: ["Property inquiries", "Viewing bookings", "Tenant communication", "Maintenance requests"],
      },
      {
        name: "E-commerce Agent",
        icon: ShoppingCart,
        handles: ["Order status updates", "Return processing", "Customer support", "Product inquiries"],
      },
    ],
  },
  {
    id: "rules",
    icon: Workflow,
    title: "Custom Rules Engine",
    description:
      "Create IF/THEN rules to automate your specific workflow. No coding required.",
    details: [
      "Visual rule builder (no code needed)",
      "Combine conditions with AND/OR logic",
      "Actions: reply, label, forward, escalate, archive",
      "Priority-based rule execution",
    ],
  },
  {
    id: "analytics",
    icon: BarChart3,
    title: "Analytics Dashboard",
    description:
      "Real-time insights into your email processing. Track volume, response times, categories, and agent performance.",
    details: [
      "Real-time email volume charts",
      "Response time tracking",
      "Category distribution breakdown",
      "Weekly comparison reports",
      "Top sender analysis",
      "Export data to CSV",
    ],
  },
  {
    id: "whatsapp",
    icon: Smartphone,
    title: "WhatsApp Integration",
    description:
      "Get instant WhatsApp notifications for urgent or escalated emails. Never miss a critical message even when away from your inbox.",
    details: [
      "Instant escalation alerts",
      "Configurable trigger rules",
      "Rich message with email preview",
      "One-tap to view full email",
    ],
  },
  {
    id: "security",
    icon: Lock,
    title: "Enterprise Security",
    description:
      "Your data security is our priority. We use industry-standard encryption and follow best practices for data protection.",
    details: [
      "OAuth 2.0 Gmail authentication",
      "End-to-end encryption in transit",
      "No email content stored permanently",
      "Full audit logs for all actions",
      "GDPR-compliant data handling",
      "Regular security audits",
    ],
  },
  {
    id: "self-healing",
    icon: HeartPulse,
    title: "Self-Healing Platform",
    description:
      "Our monitoring system keeps your agent running 24/7. If something breaks, it auto-recovers before you notice.",
    details: [
      "Health checks every 5 minutes",
      "Automatic Gmail token refresh",
      "Auto-restart on agent failures",
      "Database connection recovery",
      "Error rate monitoring and alerts",
      "99.9% uptime target",
    ],
  },
  {
    id: "chatbot",
    icon: Bot,
    title: "AI Support Chatbot",
    description:
      "Get instant help from our AI support assistant. It can diagnose issues, answer questions, and guide you through any problem.",
    details: [
      "Available 24/7 on every page",
      "Powered by Claude AI",
      "Can diagnose real agent issues",
      "Escalates to human support when needed",
      "Context-aware conversations",
    ],
  },
];

// --- Component ---

export default function FeaturesPage() {
  return (
    <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
      {/* Hero */}
      <div className="text-center">
        <h1 className="text-3xl font-bold tracking-tight text-text sm:text-4xl lg:text-5xl">
          Every feature your inbox needs
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-lg text-text-3">
          Powerful AI tools that transform how you handle email, built for every industry.
        </p>
      </div>

      {/* Feature sections */}
      <div className="mt-20 space-y-24">
        {featureSections.map((section, idx) => (
          <div
            key={section.id}
            className={cn(
              "flex flex-col gap-8 lg:flex-row lg:items-start lg:gap-16",
              idx % 2 === 1 && "lg:flex-row-reverse"
            )}
          >
            {/* Text side */}
            <div className="flex-1">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy/10">
                  <section.icon className="h-5 w-5 text-navy" />
                </div>
                <h2 className="text-xl font-bold text-text sm:text-2xl">
                  {section.title}
                </h2>
              </div>

              <p className="mt-4 text-text-3 leading-relaxed">
                {section.description}
              </p>

              {section.details && (
                <ul className="mt-4 space-y-2">
                  {section.details.map((d) => (
                    <li
                      key={d}
                      className="flex items-start gap-2 text-sm text-text-2"
                    >
                      <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                      {d}
                    </li>
                  ))}
                </ul>
              )}
            </div>

            {/* Visual side */}
            <div className="flex-1">
              {/* Classification categories example */}
              {section.id === "classification" && (
                <Card>
                  <CardBody className="p-5">
                    <p className="text-xs font-medium text-text-3">
                      Example categories
                    </p>
                    <div className="mt-3 flex flex-wrap gap-2">
                      {[
                        { category: "Job Application", color: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400" },
                        { category: "Property Inquiry", color: "bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400" },
                        { category: "Order Status", color: "bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400" },
                        { category: "Meeting Request", color: "bg-violet-100 text-violet-700 dark:bg-violet-900/30 dark:text-violet-400" },
                        { category: "Spam", color: "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400" },
                      ].map((item) => (
                        <span
                          key={item.category}
                          className={cn(
                            "rounded-full px-3 py-1 text-xs font-medium",
                            item.color
                          )}
                        >
                          {item.category}
                        </span>
                      ))}
                    </div>
                  </CardBody>
                </Card>
              )}

              {/* Reply before/after example */}
              {section.id === "replies" && (
                <Card>
                  <CardBody className="space-y-4 p-5">
                    <div>
                      <Badge variant="warning" size="sm">Incoming</Badge>
                      <p className="mt-2 text-sm text-text-3 italic">
                        &ldquo;Hi, I&apos;d like to schedule a viewing for the 3-bed apartment on Park Road. Is Saturday available?&rdquo;
                      </p>
                    </div>
                    <div className="border-t border-border pt-4">
                      <Badge variant="success" size="sm">AI Reply</Badge>
                      <p className="mt-2 text-sm text-text-2">
                        &ldquo;Thank you for your interest in the 3-bedroom apartment on Park Road! Saturday viewings are available at 10am, 12pm, and 3pm. Which time works best for you? I&apos;ll send a confirmation with the full address and parking details.&rdquo;
                      </p>
                    </div>
                  </CardBody>
                </Card>
              )}

              {/* Safety - shield visual */}
              {section.id === "safety" && (
                <Card className="border-success/30 bg-success/5">
                  <CardBody className="p-5 text-center">
                    <ShieldCheck className="mx-auto h-16 w-16 text-success" />
                    <p className="mt-3 text-sm font-semibold text-text">
                      Enterprise-grade safety
                    </p>
                    <p className="mt-1 text-xs text-text-3">
                      Every action is logged and auditable
                    </p>
                  </CardBody>
                </Card>
              )}

              {/* Industry agents grid */}
              {section.id === "agents" && section.agents && (
                <div className="grid gap-3 sm:grid-cols-2">
                  {section.agents.map((agent) => (
                    <Card key={agent.name} hover>
                      <CardBody className="p-4">
                        <div className="flex items-center gap-2">
                          <agent.icon className="h-4 w-4 text-navy" />
                          <p className="text-sm font-semibold text-text">
                            {agent.name}
                          </p>
                        </div>
                        <ul className="mt-2 space-y-1">
                          {agent.handles.map((h) => (
                            <li
                              key={h}
                              className="text-xs text-text-3"
                            >
                              &bull; {h}
                            </li>
                          ))}
                        </ul>
                      </CardBody>
                    </Card>
                  ))}
                </div>
              )}

              {/* Rules engine example */}
              {section.id === "rules" && (
                <Card>
                  <CardBody className="p-5">
                    <p className="text-xs font-medium text-text-3">
                      Example rule
                    </p>
                    <div className="mt-3 space-y-3">
                      <div className="rounded-lg bg-navy/5 px-4 py-3">
                        <p className="text-xs font-semibold text-navy">IF</p>
                        <p className="mt-1 text-sm text-text-2">
                          Email contains &quot;urgent&quot; AND sender is VIP client
                        </p>
                      </div>
                      <div className="flex justify-center">
                        <ArrowRight className="h-4 w-4 text-text-4" />
                      </div>
                      <div className="rounded-lg bg-success/5 px-4 py-3">
                        <p className="text-xs font-semibold text-success">THEN</p>
                        <p className="mt-1 text-sm text-text-2">
                          Auto-reply with acknowledgment &rarr; Escalate to WhatsApp &rarr; Label as Priority
                        </p>
                      </div>
                    </div>
                  </CardBody>
                </Card>
              )}

              {/* Analytics chart placeholder */}
              {section.id === "analytics" && (
                <Card>
                  <CardBody className="p-5">
                    <p className="text-xs font-medium text-text-3">
                      Dashboard preview
                    </p>
                    <div className="mt-3 space-y-2">
                      {["Mon", "Tue", "Wed", "Thu", "Fri"].map((day, i) => {
                        const widths = [60, 85, 70, 90, 75];
                        return (
                          <div key={day} className="flex items-center gap-3">
                            <span className="w-8 text-xs text-text-4">{day}</span>
                            <div className="flex-1">
                              <div
                                className="h-4 rounded bg-navy/20"
                                style={{ width: `${widths[i]}%` }}
                              >
                                <div
                                  className="h-full rounded bg-navy transition-all"
                                  style={{ width: `${widths[i] - 15}%` }}
                                />
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                    <div className="mt-3 flex gap-4 text-xs text-text-4">
                      <span className="flex items-center gap-1">
                        <span className="h-2 w-2 rounded-full bg-navy" /> Auto-handled
                      </span>
                      <span className="flex items-center gap-1">
                        <span className="h-2 w-2 rounded-full bg-navy/20" /> Total
                      </span>
                    </div>
                  </CardBody>
                </Card>
              )}

              {/* WhatsApp notification preview */}
              {section.id === "whatsapp" && (
                <Card className="border-green-500/30 bg-green-50 dark:bg-green-950/20">
                  <CardBody className="p-5">
                    <div className="flex items-center gap-2">
                      <Smartphone className="h-4 w-4 text-green-600" />
                      <p className="text-xs font-medium text-green-700 dark:text-green-400">
                        WhatsApp notification preview
                      </p>
                    </div>
                    <div className="mt-3 rounded-lg bg-white p-4 text-sm text-gray-700 shadow-sm dark:bg-gray-900 dark:text-gray-300">
                      <pre className="whitespace-pre-wrap font-sans text-xs">
                        {`🚨 Urgent Email Escalated\n\nFrom: CEO@company.com\nSubject: Q1 Board Meeting - Action Required\n\nThis email was flagged as urgent. Tap to view →`}
                      </pre>
                    </div>
                  </CardBody>
                </Card>
              )}

              {/* Security badges */}
              {section.id === "security" && (
                <Card>
                  <CardBody className="p-5">
                    <div className="grid grid-cols-2 gap-4">
                      {[
                        { label: "OAuth 2.0", sub: "Authentication" },
                        { label: "AES-256", sub: "Encryption" },
                        { label: "GDPR", sub: "Compliant" },
                        { label: "SOC 2", sub: "In Progress" },
                      ].map((b) => (
                        <div
                          key={b.label}
                          className="rounded-lg border border-border p-3 text-center"
                        >
                          <p className="text-sm font-bold text-text">{b.label}</p>
                          <p className="text-xs text-text-4">{b.sub}</p>
                        </div>
                      ))}
                    </div>
                  </CardBody>
                </Card>
              )}

              {/* Self-healing uptime */}
              {section.id === "self-healing" && (
                <Card>
                  <CardBody className="p-5 text-center">
                    <p className="text-5xl font-bold text-success">99.9%</p>
                    <p className="mt-2 text-sm font-medium text-text">
                      Uptime Target
                    </p>
                    <p className="mt-1 text-xs text-text-3">
                      Automated monitoring &amp; recovery every 5 minutes
                    </p>
                  </CardBody>
                </Card>
              )}

              {/* Chatbot preview */}
              {section.id === "chatbot" && (
                <Card>
                  <CardBody className="p-5">
                    <div className="space-y-3">
                      <div className="flex gap-2">
                        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-navy/10">
                          <Bot className="h-3 w-3 text-navy" />
                        </div>
                        <div className="rounded-lg rounded-tl-none bg-background-1 px-3 py-2 text-xs text-text-2">
                          Hi! How can I help you today?
                        </div>
                      </div>
                      <div className="flex flex-row-reverse gap-2">
                        <div className="rounded-lg rounded-tr-none bg-navy px-3 py-2 text-xs text-white">
                          My agent stopped processing emails
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <div className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-navy/10">
                          <Bot className="h-3 w-3 text-navy" />
                        </div>
                        <div className="rounded-lg rounded-tl-none bg-background-1 px-3 py-2 text-xs text-text-2">
                          I checked your agent — your Gmail token expired. Click
                          &quot;Reconnect Gmail&quot; in Settings to fix it.
                        </div>
                      </div>
                    </div>
                  </CardBody>
                </Card>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Bottom CTA */}
      <div className="mt-24 rounded-2xl bg-navy p-8 text-center sm:p-12">
        <h2 className="text-2xl font-bold text-white sm:text-3xl">
          Ready to automate your inbox?
        </h2>
        <p className="mx-auto mt-3 max-w-md text-sm text-white/70">
          Start your free 7-day trial. No credit card required. Set up in under
          10 minutes.
        </p>
        <Link href="/signup" className="mt-6 inline-block">
          <Button
            size="lg"
            className="bg-white text-navy hover:bg-white/90"
          >
            Start Free Trial &rarr;
          </Button>
        </Link>
      </div>
    </div>
  );
}
