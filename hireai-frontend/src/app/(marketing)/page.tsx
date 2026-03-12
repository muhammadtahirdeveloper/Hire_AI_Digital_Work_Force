import type { Metadata } from "next";
import { HeroSection } from "@/components/marketing/landing/hero-section";
import { StatsSection } from "@/components/marketing/landing/stats-section";
import { DashboardPreview } from "@/components/marketing/landing/dashboard-preview";
import { FeaturesSection } from "@/components/marketing/landing/features-section";
import { HowItWorksSection } from "@/components/marketing/landing/how-it-works-section";
import { ChatbotPreview } from "@/components/marketing/landing/chatbot-preview";
import { ReviewsSection } from "@/components/marketing/landing/reviews-section";
import { PricingSection } from "@/components/marketing/landing/pricing-section";
import { FAQSection } from "@/components/marketing/landing/faq-section";
import { CTASection } from "@/components/marketing/landing/cta-section";
import { Footer } from "@/components/marketing/landing/footer";

export const metadata: Metadata = {
  title: "HireAI — Intelligent Email Agents for Every Industry",
  description:
    "AI agents that read, classify, and respond to your emails automatically. Specialized for HR, Real Estate, E-commerce, and more.",
  keywords: [
    "AI email agent",
    "email automation",
    "Gmail agent",
    "HR email automation",
    "real estate email agent",
    "e-commerce email agent",
    "AI inbox assistant",
  ],
};

export default function LandingPage() {
  return (
    <>
      <HeroSection />
      <StatsSection />
      <DashboardPreview />
      <FeaturesSection />
      <HowItWorksSection />
      <ChatbotPreview />
      <ReviewsSection />
      <PricingSection />
      <FAQSection />
      <CTASection />
      <Footer />
    </>
  );
}
