import type { Metadata } from "next";
import { Footer } from "@/components/marketing/landing/footer";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description:
    "HireAI privacy policy — how we collect, use, and protect your data.",
};

const sections = [
  {
    title: "1. Information We Collect",
    content: [
      "Account information: When you sign up, we collect your name, email address, and password. If you sign up via Google OAuth, we receive your Google profile information.",
      "Email data: When you connect your Gmail account, our AI agents access your emails to classify, summarize, and generate replies. We process email metadata (sender, subject, timestamps) and email body content.",
      "Usage data: We collect information about how you interact with our platform, including pages visited, features used, agent configurations, and performance metrics.",
      "Device and browser data: We automatically collect your IP address, browser type, operating system, and device identifiers for security and analytics purposes.",
    ],
  },
  {
    title: "2. How We Use Your Data",
    content: [
      "To provide and improve our AI email agent services, including email classification, reply generation, and workflow automation.",
      "To personalize your experience and train your agent to better match your communication style and business needs.",
      "To send you service-related notifications, security alerts, and product updates.",
      "To monitor and improve platform performance, reliability, and security.",
      "To comply with legal obligations and enforce our terms of service.",
    ],
  },
  {
    title: "3. Email Data Processing",
    content: [
      "Your email content is processed in real-time by our AI agents and is not stored permanently on our servers. We retain email metadata (sender, subject, category) for analytics and agent performance tracking.",
      "We never share your email content with third parties. Our AI models do not use your email data for training purposes beyond your own agent personalization.",
      "You can disconnect your Gmail account at any time, which immediately stops all email processing and deletes associated data within 30 days.",
    ],
  },
  {
    title: "4. API Key Security (BYOK)",
    content: [
      "If you choose to bring your own API key (BYOK), your key is encrypted using AES-256 encryption before being stored in our database.",
      "Your API key is only decrypted in-memory during agent execution and is never logged, displayed, or transmitted to any third party.",
      "We do not have access to your API key in plain text. If you lose your key, you must generate a new one from your AI provider.",
      "You can update or remove your API key at any time through your dashboard settings.",
    ],
  },
  {
    title: "5. Custom Database Security",
    content: [
      "If you connect your own PostgreSQL database, your connection URL is encrypted using AES-256 encryption.",
      "All data processed by your agent is stored directly in your database — HireAI does not retain copies.",
      "We test the database connection only when you explicitly request it. No persistent connections are maintained outside of agent execution.",
      "If your custom database becomes unavailable, your agent will pause automatically until connectivity is restored.",
    ],
  },
  {
    title: "6. Notification Data Handling",
    content: [
      "Email notifications (weekly summaries, expiry warnings, agent alerts) are sent from hireaidigitalemployee@gmail.com.",
      "WhatsApp notifications are sent via secure channels. Your phone number is encrypted at rest.",
      "Browser push notifications are processed locally on your device. No notification content is stored on our servers.",
      "You can manage all notification preferences through your dashboard settings.",
    ],
  },
  {
    title: "7. Billing Information",
    content: [
      "Payment processing is handled by secure third-party payment processors. We never store your full credit card details.",
      "Invoice data (plan name, amount, date) is retained for billing history and compliance purposes.",
      "Billing data is encrypted at rest and accessible only to you through your account settings.",
    ],
  },
  {
    title: "8. AI Provider Data Usage",
    content: [
      "When using HireAI-managed API keys, your email data is sent to the respective AI provider (Groq, OpenAI, or Anthropic) for processing.",
      "Each AI provider has its own data usage policy. HireAI-managed keys use API-only access, which means your data is NOT used for model training by any provider.",
      "When using BYOK, your data is subject to the terms of your API key agreement with the respective provider.",
      "We recommend reviewing the privacy policies of your chosen AI provider for complete details.",
    ],
  },
  {
    title: "9. Cookies & Tracking",
    content: [
      "We use essential cookies to maintain your session and authentication state.",
      "We use analytics cookies to understand how users interact with our platform. You can disable non-essential cookies through your browser settings.",
      "We do not sell your data to advertisers or use third-party advertising trackers.",
    ],
  },
  {
    title: "10. Third-Party Services",
    content: [
      "Google OAuth: Used for authentication and Gmail access. Subject to Google's privacy policy.",
      "Payment processors: We use secure third-party payment processors for subscription billing. We never store your full credit card details.",
      "Cloud infrastructure: Our platform runs on secure cloud providers with SOC 2 compliance and data encryption at rest and in transit.",
    ],
  },
  {
    title: "11. Data Security",
    content: [
      "We use industry-standard encryption (AES-256) for data at rest and TLS 1.3 for data in transit.",
      "Access to user data is restricted to authorized personnel with role-based access controls.",
      "We conduct regular security audits and vulnerability assessments.",
      "All API endpoints are protected with authentication and rate limiting.",
    ],
  },
  {
    title: "12. Your Rights",
    content: [
      "Access: You can request a copy of all personal data we hold about you.",
      "Correction: You can update or correct your personal information at any time through your account settings.",
      "Deletion: You can request complete deletion of your account and all associated data. We will process deletion requests within 30 days.",
      "Portability: You can export your data in a machine-readable format.",
      "Opt-out: You can opt out of non-essential communications at any time.",
    ],
  },
  {
    title: "13. Data Retention",
    content: [
      "Account data is retained for as long as your account is active.",
      "Email metadata and analytics are retained for 12 months after processing.",
      "After account deletion, all data is permanently removed within 30 days.",
      "Backup copies may persist for up to 90 days after deletion for disaster recovery purposes.",
    ],
  },
  {
    title: "14. Changes to This Policy",
    content: [
      "We may update this privacy policy from time to time. We will notify you of significant changes via email or through a prominent notice on our platform.",
      "Continued use of our services after changes constitutes acceptance of the updated policy.",
    ],
  },
];

export default function PrivacyPage() {
  return (
    <>
      <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight text-text sm:text-4xl">
            Privacy Policy
          </h1>
          <p className="mt-4 text-text-3">
            Last updated: March 15, 2026
          </p>
        </div>

        {/* Intro */}
        <div className="mt-12 rounded-xl border border-border bg-background-1 p-6">
          <p className="text-sm leading-relaxed text-text-2">
            At HireAI, we take your privacy seriously. This policy explains how
            we collect, use, store, and protect your personal information when
            you use our AI email agent platform. By using HireAI, you agree to
            the practices described in this policy.
          </p>
        </div>

        {/* Sections */}
        <div className="mt-12 space-y-10">
          {sections.map((section) => (
            <div key={section.title}>
              <h2 className="text-xl font-bold text-text">{section.title}</h2>
              <ul className="mt-4 space-y-3">
                {section.content.map((item, i) => (
                  <li
                    key={i}
                    className="flex items-start gap-3 text-sm leading-relaxed text-text-2"
                  >
                    <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-navy" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Contact */}
        <div className="mt-16 rounded-xl border border-border bg-background-1 p-6 text-center">
          <h2 className="text-lg font-bold text-text">
            Questions about your privacy?
          </h2>
          <p className="mt-2 text-sm text-text-3">
            Contact our privacy team at{" "}
            <a
              href="mailto:hireaidigitalemployee@gmail.com"
              className="font-medium text-navy hover:underline"
            >
              hireaidigitalemployee@gmail.com
            </a>
          </p>
        </div>
      </div>
      <Footer />
    </>
  );
}
