"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Rocket,
  Mail,
  Bot,
  Code,
  HelpCircle,
  ChevronDown,
  Check,
  ArrowRight,
} from "lucide-react";
import { Card, CardBody } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Footer } from "@/components/marketing/landing/footer";

// --- Getting Started Steps ---

const gettingStartedSteps = [
  {
    step: 1,
    title: "Create your account",
    description:
      "Sign up with your email or Google account. No credit card required for the free trial.",
  },
  {
    step: 2,
    title: "Connect your Gmail",
    description:
      "Click \"Connect Gmail\" on the dashboard and authorize HireAI via Google OAuth. We only request the permissions needed to read and send emails.",
  },
  {
    step: 3,
    title: "Choose your agent",
    description:
      "Select an industry-specific agent (General, HR, Real Estate, or E-commerce) or start with the General agent.",
  },
  {
    step: 4,
    title: "Configure rules (optional)",
    description:
      "Set up custom IF/THEN rules to automate specific workflows. For example: if an email contains \"invoice\", label it as Finance and forward to your accountant.",
  },
  {
    step: 5,
    title: "Activate your agent",
    description:
      "Turn on your agent and it will start processing incoming emails immediately. Monitor its activity on the dashboard.",
  },
];

// --- Gmail Connection Guide ---

const gmailSteps = [
  {
    title: "Navigate to Settings",
    description: "Go to your HireAI dashboard and click Settings in the sidebar.",
  },
  {
    title: "Click Connect Gmail",
    description:
      "In the Gmail Integration section, click the \"Connect Gmail\" button.",
  },
  {
    title: "Authorize with Google",
    description:
      "A Google OAuth popup will appear. Select your Gmail account and click \"Allow\" to grant HireAI access.",
  },
  {
    title: "Verify Connection",
    description:
      "Once connected, you will see a green \"Connected\" badge next to your email address. Your agent can now process emails.",
  },
];

// --- How Agents Work ---

const agentFeatures = [
  {
    title: "Email Classification",
    description:
      "When a new email arrives, the agent analyzes the content and classifies it into categories like HR, Sales, Support, or custom categories you define.",
  },
  {
    title: "Smart Reply Generation",
    description:
      "Based on the classification and email context, the agent generates a professional reply. You can review it before sending or enable auto-send for trusted categories.",
  },
  {
    title: "Rule Execution",
    description:
      "Custom rules are evaluated in priority order. Actions include auto-reply, label, forward, escalate to WhatsApp, or archive.",
  },
  {
    title: "Learning & Adaptation",
    description:
      "When you edit or reject an AI-generated reply, the agent learns from your correction and improves future responses.",
  },
];

// --- API Reference ---

const apiEndpoints = [
  {
    method: "POST",
    path: "/api/auth/signup",
    description: "Create a new user account",
    body: '{ "email": "string", "password": "string", "full_name": "string" }',
  },
  {
    method: "POST",
    path: "/api/auth/login",
    description: "Authenticate and receive a session token",
    body: '{ "email": "string", "password": "string" }',
  },
  {
    method: "GET",
    path: "/api/emails",
    description: "Fetch processed emails with classification data",
    body: null,
  },
  {
    method: "GET",
    path: "/api/analytics/overview",
    description: "Get analytics dashboard data",
    body: null,
  },
  {
    method: "POST",
    path: "/api/agent/start",
    description: "Start the email processing agent",
    body: '{ "agent_type": "general | hr | realestate | ecommerce" }',
  },
  {
    method: "POST",
    path: "/api/agent/stop",
    description: "Stop the email processing agent",
    body: null,
  },
  {
    method: "GET",
    path: "/api/agent/status",
    description: "Check current agent status and health",
    body: null,
  },
];

// --- FAQ ---

const faqItems = [
  {
    question: "Is my email data secure?",
    answer:
      "Yes. We use OAuth 2.0 for Gmail access, AES-256 encryption at rest, and TLS 1.3 in transit. Email content is processed in real-time and not stored permanently. See our Privacy Policy for full details.",
  },
  {
    question: "Can I use HireAI with non-Gmail email providers?",
    answer:
      "Currently, HireAI supports Gmail only. We plan to add Outlook and other providers in a future update.",
  },
  {
    question: "What happens if the AI sends a wrong reply?",
    answer:
      "By default, all AI replies are drafts that require your approval before sending. You can enable auto-send for specific categories once you are confident in the agent's accuracy.",
  },
  {
    question: "How do I cancel my subscription?",
    answer:
      "Go to Settings > Billing and click \"Cancel Subscription\". You will retain access to paid features until the end of your current billing period.",
  },
  {
    question: "Can I connect multiple Gmail accounts?",
    answer:
      "On the Pro and Enterprise plans, you can connect multiple Gmail accounts and manage them from a single dashboard.",
  },
  {
    question: "What is the free trial?",
    answer:
      "New users get a 7-day free trial with full access to all features. No credit card is required to start the trial.",
  },
  {
    question: "How do I reset my password?",
    answer:
      "Click \"Forgot Password\" on the login page. You will receive a password reset link at your registered email address.",
  },
];

// --- Sidebar nav ---

const navItems = [
  { id: "getting-started", label: "Getting Started", icon: Rocket },
  { id: "gmail", label: "Connect Gmail", icon: Mail },
  { id: "agents", label: "How Agents Work", icon: Bot },
  { id: "api", label: "API Reference", icon: Code },
  { id: "faq", label: "FAQ", icon: HelpCircle },
];

export default function DocsPage() {
  const [openFaq, setOpenFaq] = useState<number | null>(null);

  return (
    <>
      <div className="mx-auto max-w-6xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight text-text sm:text-4xl">
            Documentation
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-lg text-text-3">
            Everything you need to get started with HireAI and make the most of
            your AI email agents.
          </p>
        </div>

        <div className="mt-12 flex flex-col gap-10 lg:flex-row">
          {/* Sidebar Nav */}
          <nav className="shrink-0 lg:w-56">
            <div className="sticky top-20 space-y-1">
              {navItems.map((item) => (
                <a
                  key={item.id}
                  href={`#${item.id}`}
                  className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-text-3 transition-colors hover:bg-background-2 hover:text-text"
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </a>
              ))}
            </div>
          </nav>

          {/* Content */}
          <div className="min-w-0 flex-1 space-y-16">
            {/* Getting Started */}
            <section id="getting-started">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy/10">
                  <Rocket className="h-5 w-5 text-navy" />
                </div>
                <h2 className="text-2xl font-bold text-text">
                  Getting Started
                </h2>
              </div>
              <p className="mt-4 text-sm text-text-3">
                Get your AI email agent up and running in 5 simple steps.
              </p>
              <div className="mt-6 space-y-4">
                {gettingStartedSteps.map((step) => (
                  <Card key={step.step}>
                    <CardBody className="flex items-start gap-4 p-5">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-navy text-sm font-bold text-white">
                        {step.step}
                      </div>
                      <div>
                        <h3 className="font-semibold text-text">
                          {step.title}
                        </h3>
                        <p className="mt-1 text-sm text-text-3">
                          {step.description}
                        </p>
                      </div>
                    </CardBody>
                  </Card>
                ))}
              </div>
            </section>

            {/* Connect Gmail */}
            <section id="gmail">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy/10">
                  <Mail className="h-5 w-5 text-navy" />
                </div>
                <h2 className="text-2xl font-bold text-text">
                  Connect Gmail
                </h2>
              </div>
              <p className="mt-4 text-sm text-text-3">
                Follow these steps to securely connect your Gmail account.
              </p>
              <div className="mt-6 space-y-4">
                {gmailSteps.map((step, i) => (
                  <div key={i} className="flex items-start gap-4">
                    <div className="mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-success/10">
                      <Check className="h-3.5 w-3.5 text-success" />
                    </div>
                    <div>
                      <h3 className="font-semibold text-text">{step.title}</h3>
                      <p className="mt-1 text-sm text-text-3">
                        {step.description}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
              <Card className="mt-6 border-navy/20 bg-navy/5">
                <CardBody className="p-5">
                  <p className="text-sm text-text-2">
                    <span className="font-semibold">Tip:</span> If your Gmail
                    token expires, go to Settings and click &quot;Reconnect
                    Gmail&quot;. Token refresh is usually handled automatically
                    by our self-healing system.
                  </p>
                </CardBody>
              </Card>
            </section>

            {/* How Agents Work */}
            <section id="agents">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy/10">
                  <Bot className="h-5 w-5 text-navy" />
                </div>
                <h2 className="text-2xl font-bold text-text">
                  How Agents Work
                </h2>
              </div>
              <p className="mt-4 text-sm text-text-3">
                HireAI agents follow a four-step pipeline for every incoming
                email.
              </p>

              {/* Pipeline visual */}
              <div className="mt-6 flex flex-wrap items-center justify-center gap-2">
                {["Receive", "Classify", "Generate Reply", "Execute Rules"].map(
                  (step, i) => (
                    <div key={step} className="flex items-center gap-2">
                      <span className="rounded-full bg-navy px-4 py-1.5 text-xs font-medium text-white">
                        {step}
                      </span>
                      {i < 3 && (
                        <ArrowRight className="h-4 w-4 text-text-4" />
                      )}
                    </div>
                  )
                )}
              </div>

              <div className="mt-8 grid gap-4 sm:grid-cols-2">
                {agentFeatures.map((feature) => (
                  <Card key={feature.title}>
                    <CardBody className="p-5">
                      <h3 className="font-semibold text-text">
                        {feature.title}
                      </h3>
                      <p className="mt-2 text-sm text-text-3">
                        {feature.description}
                      </p>
                    </CardBody>
                  </Card>
                ))}
              </div>
            </section>

            {/* API Reference */}
            <section id="api">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy/10">
                  <Code className="h-5 w-5 text-navy" />
                </div>
                <h2 className="text-2xl font-bold text-text">
                  API Reference
                </h2>
              </div>
              <p className="mt-4 text-sm text-text-3">
                Base URL:{" "}
                <code className="rounded bg-background-2 px-2 py-0.5 text-xs font-mono text-text">
                  https://hireai-backend-an68.onrender.com
                </code>
              </p>
              <p className="mt-2 text-sm text-text-3">
                All endpoints require an{" "}
                <code className="rounded bg-background-2 px-2 py-0.5 text-xs font-mono text-text">
                  Authorization: Bearer &lt;token&gt;
                </code>{" "}
                header (except signup and login).
              </p>

              <div className="mt-6 space-y-3">
                {apiEndpoints.map((endpoint) => (
                  <Card key={endpoint.path}>
                    <CardBody className="p-4">
                      <div className="flex flex-wrap items-center gap-2">
                        <Badge
                          variant={
                            endpoint.method === "GET" ? "success" : "navy"
                          }
                          size="sm"
                        >
                          {endpoint.method}
                        </Badge>
                        <code className="text-sm font-mono font-medium text-text">
                          {endpoint.path}
                        </code>
                      </div>
                      <p className="mt-2 text-sm text-text-3">
                        {endpoint.description}
                      </p>
                      {endpoint.body && (
                        <pre className="mt-2 overflow-x-auto rounded-lg bg-background-2 p-3 text-xs font-mono text-text-2">
                          {endpoint.body}
                        </pre>
                      )}
                    </CardBody>
                  </Card>
                ))}
              </div>
            </section>

            {/* FAQ */}
            <section id="faq">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy/10">
                  <HelpCircle className="h-5 w-5 text-navy" />
                </div>
                <h2 className="text-2xl font-bold text-text">
                  Frequently Asked Questions
                </h2>
              </div>

              <div className="mt-6 space-y-2">
                {faqItems.map((item, i) => (
                  <Card key={i}>
                    <CardBody className="p-0">
                      <button
                        onClick={() =>
                          setOpenFaq(openFaq === i ? null : i)
                        }
                        className="flex w-full items-center justify-between px-5 py-4 text-left"
                      >
                        <span className="text-sm font-semibold text-text">
                          {item.question}
                        </span>
                        <ChevronDown
                          className={cn(
                            "h-4 w-4 shrink-0 text-text-4 transition-transform",
                            openFaq === i && "rotate-180"
                          )}
                        />
                      </button>
                      {openFaq === i && (
                        <div className="border-t border-border px-5 py-4">
                          <p className="text-sm leading-relaxed text-text-3">
                            {item.answer}
                          </p>
                        </div>
                      )}
                    </CardBody>
                  </Card>
                ))}
              </div>
            </section>

            {/* Bottom CTA */}
            <div className="rounded-2xl bg-navy p-8 text-center sm:p-12">
              <h2 className="text-2xl font-bold text-white">
                Need more help?
              </h2>
              <p className="mx-auto mt-3 max-w-md text-sm text-white/70">
                Our support team is available to assist you with any questions or
                issues.
              </p>
              <Link href="/contact" className="mt-6 inline-block">
                <Button
                  size="lg"
                  className="bg-white text-navy hover:bg-white/90"
                >
                  Contact Support
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </div>
      <Footer />
    </>
  );
}
