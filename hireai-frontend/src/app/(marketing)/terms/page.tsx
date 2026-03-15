import type { Metadata } from "next";
import { Footer } from "@/components/marketing/landing/footer";

export const metadata: Metadata = {
  title: "Terms of Service",
  description:
    "HireAI terms of service — rules, subscriptions, and usage policies.",
};

const sections = [
  {
    title: "1. Acceptance of Terms",
    content: [
      "By creating an account or using HireAI, you agree to be bound by these Terms of Service and our Privacy Policy.",
      "If you are using HireAI on behalf of an organization, you represent that you have authority to bind that organization to these terms.",
      "We reserve the right to modify these terms at any time. Continued use after changes constitutes acceptance.",
    ],
  },
  {
    title: "2. Description of Service",
    content: [
      "HireAI provides AI-powered email agents that classify, summarize, and generate replies for your Gmail inbox.",
      "Our service includes email classification, AI reply generation, custom rules automation, analytics dashboards, and WhatsApp escalation notifications.",
      "Features may vary by subscription plan. We reserve the right to modify, suspend, or discontinue features with reasonable notice.",
    ],
  },
  {
    title: "3. Account & Usage Rules",
    content: [
      "You must provide accurate and complete information when creating your account.",
      "You are responsible for maintaining the confidentiality of your account credentials and for all activity under your account.",
      "You must not use HireAI to send spam, phishing emails, or any unsolicited bulk communications.",
      "You must not attempt to reverse-engineer, decompile, or extract source code from our platform.",
      "You must not use the service to process emails containing illegal content or to facilitate illegal activities.",
      "You must not share your account access with unauthorized users or exceed the usage limits of your plan.",
    ],
  },
  {
    title: "4. Gmail & Data Access",
    content: [
      "By connecting your Gmail account, you grant HireAI permission to read, classify, and generate responses to your emails using OAuth 2.0.",
      "You can revoke Gmail access at any time through your Google account settings or HireAI dashboard.",
      "HireAI accesses only the Gmail scopes necessary for the service. We do not access contacts, calendar, or other Google services unless explicitly authorized.",
    ],
  },
  {
    title: "5. BYOK Terms (Bring Your Own Key)",
    content: [
      "You are solely responsible for maintaining the validity and security of your own API key when using the BYOK option.",
      "If your API key is revoked, expired, or reaches its rate limit, your agent will automatically pause until a valid key is provided.",
      "HireAI is not liable for any costs incurred on your API key. You are responsible for monitoring your API usage and billing with your AI provider.",
      "You must not use stolen, shared, or unauthorized API keys. Doing so may result in immediate account termination.",
      "When using BYOK, your email data is processed according to your API provider's terms of service and data policies.",
    ],
  },
  {
    title: "6. Free API Terms",
    content: [
      "The Starter plan includes access to free AI models (Google Gemini, Groq) managed by HireAI at no additional cost.",
      "Free models may produce less accurate results compared to premium models like Claude or GPT-4. HireAI is not responsible for the quality of free model outputs.",
      "Availability of free API models depends on third-party providers and may change without notice.",
      "Free model usage is subject to rate limits imposed by the respective providers. If limits are reached, your agent may temporarily pause.",
    ],
  },
  {
    title: "7. Subscription & Billing",
    content: [
      "HireAI offers paid subscription plans: Starter ($9/month), Professional ($29/month), and Enterprise ($59/month or $39/month with BYOK).",
      "Prices are listed in USD and are subject to change with 30 days notice to existing subscribers.",
      "Payment is processed through secure third-party payment providers. By subscribing, you authorize recurring charges.",
      "You can upgrade, downgrade, or cancel your subscription at any time through your account settings.",
    ],
  },
  {
    title: "8. Plan Upgrade/Downgrade Policy",
    content: [
      "Upgrades take effect immediately. You will be charged the prorated difference for the remainder of your billing period.",
      "Downgrades take effect at the end of the current billing period. You retain access to paid features until then.",
      "When downgrading, email limits and feature access will adjust to your new plan at the start of the next billing period.",
      "If your email usage exceeds the limits of your new plan, your agent will pause until the next billing cycle or until you upgrade.",
    ],
  },
  {
    title: "9. Refund Policy",
    content: [
      "We offer a 7-day free trial for new users. No payment is required during the trial period.",
      "After the trial period, no refunds will be issued for any paid subscription charges.",
      "If you cancel during the trial period, you will not be charged.",
      "Annual subscriptions, when available, follow the same no-refund policy after the trial period.",
      "In exceptional circumstances (extended outages, billing errors), refunds may be issued at our discretion.",
    ],
  },
  {
    title: "10. Data Ownership with Custom Database",
    content: [
      "When you connect your own database, all email data, agent configurations, and analytics are stored exclusively in your database.",
      "HireAI does not retain copies of data stored in your custom database beyond what is necessary for real-time processing.",
      "You are responsible for the availability, backups, and security of your own database.",
      "If your database becomes unavailable, your agent will pause automatically. HireAI is not liable for any data loss in your custom database.",
      "Upon disconnecting your custom database, you retain full ownership of all data stored therein.",
    ],
  },
  {
    title: "11. Intellectual Property",
    content: [
      "HireAI and its original content, features, and functionality are owned by HireAI and protected by international copyright, trademark, and other intellectual property laws.",
      "Your data remains your property. We do not claim ownership over your emails, configurations, or any content processed through our platform.",
      "AI-generated replies are produced for your use. You are responsible for reviewing and approving all AI-generated content before sending.",
      "You may not use HireAI branding, logos, or trademarks without prior written consent.",
    ],
  },
  {
    title: "12. Limitation of Liability",
    content: [
      "HireAI is provided \"as is\" without warranties of any kind, whether express or implied.",
      "We do not guarantee that AI-generated replies will be accurate, appropriate, or free from errors. You are responsible for reviewing all AI output.",
      "HireAI shall not be liable for any indirect, incidental, special, consequential, or punitive damages arising from your use of the service.",
      "Our total liability for any claims arising from these terms shall not exceed the amount you paid to HireAI in the 12 months preceding the claim.",
    ],
  },
  {
    title: "13. Service Availability",
    content: [
      "We target 99.9% uptime but do not guarantee uninterrupted service. Scheduled maintenance will be announced in advance when possible.",
      "We are not liable for service disruptions caused by third-party providers (AI APIs, Google, cloud infrastructure), internet outages, or force majeure events.",
      "In the event of extended downtime exceeding 24 hours, affected paid subscribers may be eligible for service credits.",
    ],
  },
  {
    title: "14. Termination",
    content: [
      "You may terminate your account at any time by contacting support or through your account settings.",
      "We may suspend or terminate your account if you violate these terms, engage in abusive behavior, or fail to pay subscription fees.",
      "Upon termination, your data will be deleted within 30 days in accordance with our Privacy Policy.",
      "Sections relating to intellectual property, limitation of liability, and governing law survive termination.",
    ],
  },
  {
    title: "15. Governing Law",
    content: [
      "These terms are governed by and construed in accordance with applicable laws.",
      "Any disputes arising from these terms shall be resolved through binding arbitration, except where prohibited by law.",
      "You agree to resolve disputes individually and waive the right to participate in class action lawsuits.",
    ],
  },
];

export default function TermsPage() {
  return (
    <>
      <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="text-center">
          <h1 className="text-3xl font-bold tracking-tight text-text sm:text-4xl">
            Terms of Service
          </h1>
          <p className="mt-4 text-text-3">
            Last updated: March 15, 2026
          </p>
        </div>

        {/* Intro */}
        <div className="mt-12 rounded-xl border border-border bg-background-1 p-6">
          <p className="text-sm leading-relaxed text-text-2">
            Welcome to HireAI. These Terms of Service govern your use of our
            AI-powered email agent platform. Please read them carefully before
            using our services.
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
            Questions about these terms?
          </h2>
          <p className="mt-2 text-sm text-text-3">
            Contact us at{" "}
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
