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
    title: "5. Subscription & Billing",
    content: [
      "HireAI offers free and paid subscription plans. Paid plans are billed monthly or annually as selected at checkout.",
      "Prices are listed in USD and are subject to change with 30 days notice to existing subscribers.",
      "Payment is processed through secure third-party payment providers. By subscribing, you authorize recurring charges.",
      "You can upgrade, downgrade, or cancel your subscription at any time through your account settings.",
      "Downgrades take effect at the end of the current billing period. You retain access to paid features until then.",
    ],
  },
  {
    title: "6. Refund Policy",
    content: [
      "We offer a 7-day free trial for new users. No payment is required during the trial period.",
      "If you cancel within 7 days of your first paid charge, we will issue a full refund.",
      "After the 7-day window, refunds are issued at our discretion on a case-by-case basis.",
      "Annual subscriptions may be eligible for a prorated refund if cancelled within 30 days of purchase.",
      "Refunds are processed within 5-10 business days to the original payment method.",
    ],
  },
  {
    title: "7. Intellectual Property",
    content: [
      "HireAI and its original content, features, and functionality are owned by HireAI and protected by international copyright, trademark, and other intellectual property laws.",
      "Your data remains your property. We do not claim ownership over your emails, configurations, or any content processed through our platform.",
      "AI-generated replies are produced for your use. You are responsible for reviewing and approving all AI-generated content before sending.",
      "You may not use HireAI branding, logos, or trademarks without prior written consent.",
    ],
  },
  {
    title: "8. Limitation of Liability",
    content: [
      "HireAI is provided \"as is\" without warranties of any kind, whether express or implied.",
      "We do not guarantee that AI-generated replies will be accurate, appropriate, or free from errors. You are responsible for reviewing all AI output.",
      "HireAI shall not be liable for any indirect, incidental, special, consequential, or punitive damages arising from your use of the service.",
      "Our total liability for any claims arising from these terms shall not exceed the amount you paid to HireAI in the 12 months preceding the claim.",
      "We are not liable for any losses resulting from unauthorized access to your account due to your failure to secure your credentials.",
    ],
  },
  {
    title: "9. Service Availability",
    content: [
      "We target 99.9% uptime but do not guarantee uninterrupted service. Scheduled maintenance will be announced in advance when possible.",
      "We are not liable for service disruptions caused by third-party providers, internet outages, or force majeure events.",
      "In the event of extended downtime exceeding 24 hours, affected paid subscribers may be eligible for service credits.",
    ],
  },
  {
    title: "10. Termination",
    content: [
      "You may terminate your account at any time by contacting support or through your account settings.",
      "We may suspend or terminate your account if you violate these terms, engage in abusive behavior, or fail to pay subscription fees.",
      "Upon termination, your data will be deleted within 30 days in accordance with our Privacy Policy.",
      "Sections relating to intellectual property, limitation of liability, and governing law survive termination.",
    ],
  },
  {
    title: "11. Governing Law",
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
            Last updated: January 15, 2025
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
