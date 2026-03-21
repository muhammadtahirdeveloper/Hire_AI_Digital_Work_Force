"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Check,
  Building2,
  Users,
  Palette,
  Globe,
  BarChart3,
  ArrowRight,
  Star,
  TrendingUp,
  Shield,
  Zap,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardBody } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import toast from "react-hot-toast";

// --- Agency Plans ---

const agencyPlans = [
  {
    id: "agency_starter",
    name: "Agency Starter",
    price: 99,
    annualPrice: 79,
    maxUsers: 10,
    popular: false,
    profitExample: "$19/user x 10 = $190/mo revenue",
    profitAmount: "$91/mo profit",
    features: [
      "Up to 10 users",
      "White-label branding",
      "Custom logo & colors",
      "Subdomain (name.hireai.app)",
      "User management dashboard",
      "Usage analytics",
      "Email support",
    ],
  },
  {
    id: "agency_pro",
    name: "Agency Pro",
    price: 249,
    annualPrice: 199,
    maxUsers: 50,
    popular: true,
    profitExample: "$15/user x 50 = $750/mo revenue",
    profitAmount: "$501/mo profit",
    features: [
      "Up to 50 users",
      "Everything in Starter",
      "Custom domain support",
      "Advanced analytics",
      "Priority support",
      "Export usage reports",
      "Per-user email limits",
    ],
  },
  {
    id: "agency_enterprise",
    name: "Agency Enterprise",
    price: 499,
    annualPrice: 399,
    maxUsers: 9999,
    popular: false,
    profitExample: "$10/user x 100 = $1,000/mo revenue",
    profitAmount: "$501/mo profit",
    features: [
      "Unlimited users",
      "Everything in Pro",
      "Dedicated support",
      "Custom agent training",
      "SLA guarantee",
      "API access",
      "White-glove onboarding",
    ],
  },
];

const benefits = [
  {
    icon: Palette,
    title: "Your Brand, Your Product",
    description: "Replace HireAI branding with your own logo, colors, and name. Your clients never see HireAI.",
  },
  {
    icon: Users,
    title: "Manage All Users",
    description: "Add, remove, and monitor users from a single dashboard. Set per-user limits and permissions.",
  },
  {
    icon: Globe,
    title: "Custom Domain",
    description: "Get your own subdomain (you.hireai.app) or connect your custom domain (ai.yourbrand.com).",
  },
  {
    icon: TrendingUp,
    title: "Set Your Own Pricing",
    description: "Buy at wholesale, sell at your price. Keep 100% of the margin. No revenue sharing.",
  },
  {
    icon: BarChart3,
    title: "Analytics & Reports",
    description: "See per-user usage, export reports, and track ROI for your agency and each client.",
  },
  {
    icon: Shield,
    title: "Enterprise Security",
    description: "SOC 2 compliant infrastructure. Data isolation per tenant. OAuth2 authentication.",
  },
];

// --- Page ---

export default function ResellerPage() {
  const [annual, setAnnual] = useState(false);
  const [formData, setFormData] = useState({
    company_name: "",
    contact_name: "",
    email: "",
    phone: "",
    slug: "",
    plan: "agency_starter",
  });
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const handleSlugChange = (value: string) => {
    const slug = value.toLowerCase().replace(/[^a-z0-9-]/g, "").slice(0, 32);
    setFormData((prev) => ({ ...prev, slug }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.company_name || !formData.email || !formData.slug) {
      toast.error("Please fill in all required fields");
      return;
    }
    setSubmitting(true);
    try {
      await api.post("/api/agency/signup", formData);
      setSubmitted(true);
      toast.success("Agency account created! Check your email.");
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Signup failed. Please try again.";
      toast.error(message);
    }
    setSubmitting(false);
  };

  return (
    <div className="min-h-screen">
      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-navy/5 via-background to-navy/5 px-4 py-20 sm:py-28">
        <div className="mx-auto max-w-5xl text-center">
          <Badge variant="navy" className="mb-4">
            <Building2 className="mr-1 h-3 w-3" />
            Reseller Program
          </Badge>
          <h1 className="text-4xl font-bold tracking-tight text-text sm:text-5xl lg:text-6xl">
            Sell AI Email Agents
            <br />
            <span className="text-navy">Under Your Brand</span>
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-text-3">
            White-label HireAI and resell to your clients at your own price.
            Your branding, your pricing, your profit. We handle the technology.
          </p>
          <div className="mt-8 flex items-center justify-center gap-4">
            <a href="#signup">
              <Button size="lg" leftIcon={<ArrowRight className="h-5 w-5" />}>
                Start Free Trial
              </Button>
            </a>
            <a href="#pricing">
              <Button variant="outline" size="lg">
                View Pricing
              </Button>
            </a>
          </div>
          <p className="mt-4 text-sm text-text-4">
            14-day free trial &middot; No credit card required &middot; Cancel anytime
          </p>
        </div>
      </section>

      {/* How It Works */}
      <section className="border-t border-border px-4 py-16">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-center text-2xl font-bold text-text sm:text-3xl">
            How It Works
          </h2>
          <div className="mt-12 grid gap-8 sm:grid-cols-3">
            {[
              { step: "1", title: "Sign Up", desc: "Create your agency account and choose a plan. Get a 14-day free trial." },
              { step: "2", title: "Customize", desc: "Add your logo, colors, and brand name. Set up your custom domain." },
              { step: "3", title: "Sell & Profit", desc: "Invite your clients, set your own pricing. Keep 100% of the margin." },
            ].map((item) => (
              <div key={item.step} className="text-center">
                <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-navy text-xl font-bold text-white">
                  {item.step}
                </div>
                <h3 className="mt-4 text-lg font-semibold text-text">{item.title}</h3>
                <p className="mt-2 text-sm text-text-3">{item.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="border-t border-border bg-background-1 px-4 py-16">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-center text-2xl font-bold text-text sm:text-3xl">
            Why Agencies Choose HireAI
          </h2>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
            {benefits.map((b) => (
              <Card key={b.title} hover>
                <CardBody className="p-6">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy/10">
                    <b.icon className="h-5 w-5 text-navy" />
                  </div>
                  <h3 className="mt-4 text-sm font-semibold text-text">{b.title}</h3>
                  <p className="mt-2 text-xs text-text-3">{b.description}</p>
                </CardBody>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing */}
      <section id="pricing" className="border-t border-border px-4 py-16">
        <div className="mx-auto max-w-5xl">
          <h2 className="text-center text-2xl font-bold text-text sm:text-3xl">
            Agency Pricing
          </h2>
          <p className="mx-auto mt-3 max-w-xl text-center text-text-3">
            Buy at wholesale. Sell at your price. Keep the profit.
          </p>

          {/* Annual Toggle */}
          <div className="mt-8 flex items-center justify-center gap-3">
            <span className={cn("text-sm", !annual ? "font-semibold text-text" : "text-text-3")}>
              Monthly
            </span>
            <button
              onClick={() => setAnnual(!annual)}
              className={cn(
                "relative h-6 w-11 rounded-full transition-colors",
                annual ? "bg-navy" : "bg-border-2"
              )}
            >
              <span
                className={cn(
                  "absolute top-0.5 left-0.5 h-5 w-5 rounded-full bg-white transition-transform",
                  annual && "translate-x-5"
                )}
              />
            </button>
            <span className={cn("text-sm", annual ? "font-semibold text-text" : "text-text-3")}>
              Annual
              <Badge variant="success" size="sm" className="ml-1.5">
                Save 20%
              </Badge>
            </span>
          </div>

          {/* Plan Cards */}
          <div className="mt-10 grid gap-6 lg:grid-cols-3">
            {agencyPlans.map((plan) => (
              <Card
                key={plan.id}
                className={cn(
                  "relative",
                  plan.popular && "border-navy ring-1 ring-navy"
                )}
              >
                {plan.popular && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge variant="navy">
                      <Star className="mr-1 h-3 w-3" /> Most Popular
                    </Badge>
                  </div>
                )}
                <CardBody className="p-6">
                  <h3 className="text-lg font-semibold text-text">{plan.name}</h3>
                  <div className="mt-3">
                    <span className="text-4xl font-bold text-text">
                      ${annual ? plan.annualPrice : plan.price}
                    </span>
                    <span className="text-text-3">/mo</span>
                  </div>
                  <p className="mt-1 text-xs text-text-4">
                    {plan.maxUsers === 9999 ? "Unlimited" : `Up to ${plan.maxUsers}`} users
                  </p>

                  {/* Profit Example */}
                  <div className="mt-4 rounded-lg bg-success/10 p-3">
                    <p className="text-xs font-medium text-success">
                      <TrendingUp className="mr-1 inline h-3 w-3" />
                      {plan.profitExample}
                    </p>
                    <p className="mt-0.5 text-sm font-bold text-success">
                      {plan.profitAmount}
                    </p>
                  </div>

                  <ul className="mt-6 space-y-2.5">
                    {plan.features.map((f) => (
                      <li key={f} className="flex items-start gap-2 text-sm text-text-2">
                        <Check className="mt-0.5 h-4 w-4 shrink-0 text-success" />
                        {f}
                      </li>
                    ))}
                  </ul>

                  <a href="#signup">
                    <Button
                      className="mt-6 w-full"
                      variant={plan.popular ? "primary" : "outline"}
                      onClick={() =>
                        setFormData((prev) => ({ ...prev, plan: plan.id }))
                      }
                    >
                      Start Free Trial
                    </Button>
                  </a>
                </CardBody>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Demo Section */}
      <section className="border-t border-border bg-background-1 px-4 py-16">
        <div className="mx-auto max-w-3xl text-center">
          <Zap className="mx-auto h-10 w-10 text-navy" />
          <h2 className="mt-4 text-2xl font-bold text-text">See HireAI in Action</h2>
          <p className="mt-3 text-text-3">
            Try our live demo to see how the AI email agent processes, classifies,
            and responds to emails automatically.
          </p>
          <div className="mt-6 flex items-center justify-center gap-4">
            <Link href="/login">
              <Button>Try Live Demo</Button>
            </Link>
            <Link href="/features">
              <Button variant="outline">View Features</Button>
            </Link>
          </div>
        </div>
      </section>

      {/* Signup Form */}
      <section id="signup" className="border-t border-border px-4 py-16">
        <div className="mx-auto max-w-xl">
          <h2 className="text-center text-2xl font-bold text-text">
            Start Your Agency
          </h2>
          <p className="mt-2 text-center text-text-3">
            14-day free trial. No credit card required.
          </p>

          {submitted ? (
            <Card className="mt-8">
              <CardBody className="p-8 text-center">
                <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-success/10">
                  <Check className="h-8 w-8 text-success" />
                </div>
                <h3 className="mt-4 text-lg font-semibold text-text">
                  Agency Created!
                </h3>
                <p className="mt-2 text-sm text-text-3">
                  Your portal is ready at{" "}
                  <strong className="text-navy">
                    {formData.slug}.hireai.app
                  </strong>
                </p>
                <p className="mt-1 text-xs text-text-4">
                  Check your email for login instructions and setup guide.
                </p>
                <Link href="/login" className="mt-6 inline-block">
                  <Button>Go to Dashboard</Button>
                </Link>
              </CardBody>
            </Card>
          ) : (
            <form onSubmit={handleSubmit} className="mt-8 space-y-4">
              <Card>
                <CardBody className="space-y-4 p-6">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Input
                      label="Company Name *"
                      placeholder="TechCorp"
                      value={formData.company_name}
                      onChange={(e) =>
                        setFormData((prev) => ({ ...prev, company_name: e.target.value }))
                      }
                      required
                    />
                    <Input
                      label="Your Name *"
                      placeholder="John Doe"
                      value={formData.contact_name}
                      onChange={(e) =>
                        setFormData((prev) => ({ ...prev, contact_name: e.target.value }))
                      }
                      required
                    />
                  </div>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <Input
                      label="Email *"
                      type="email"
                      placeholder="john@techcorp.com"
                      value={formData.email}
                      onChange={(e) =>
                        setFormData((prev) => ({ ...prev, email: e.target.value }))
                      }
                      required
                    />
                    <Input
                      label="Phone"
                      type="tel"
                      placeholder="+1 234 567 8900"
                      value={formData.phone}
                      onChange={(e) =>
                        setFormData((prev) => ({ ...prev, phone: e.target.value }))
                      }
                    />
                  </div>

                  {/* Subdomain */}
                  <div className="space-y-1.5">
                    <label className="block text-sm font-medium text-text-2">
                      Choose Your Subdomain *
                    </label>
                    <div className="flex items-center">
                      <Input
                        placeholder="techcorp"
                        value={formData.slug}
                        onChange={(e) => handleSlugChange(e.target.value)}
                        className="rounded-r-none"
                        required
                      />
                      <span className="flex h-10 items-center rounded-r-lg border border-l-0 border-border bg-background-2 px-3 text-sm text-text-3">
                        .hireai.app
                      </span>
                    </div>
                    {formData.slug && (
                      <p className="text-xs text-text-4">
                        Your portal: <strong className="text-navy">{formData.slug}.hireai.app</strong>
                      </p>
                    )}
                  </div>

                  {/* Plan Selection */}
                  <div className="space-y-1.5">
                    <label className="block text-sm font-medium text-text-2">
                      Plan
                    </label>
                    <div className="grid grid-cols-3 gap-2">
                      {agencyPlans.map((plan) => (
                        <button
                          key={plan.id}
                          type="button"
                          onClick={() =>
                            setFormData((prev) => ({ ...prev, plan: plan.id }))
                          }
                          className={cn(
                            "rounded-lg border-2 p-3 text-left transition-all",
                            formData.plan === plan.id
                              ? "border-navy bg-navy/5"
                              : "border-border hover:border-border-2"
                          )}
                        >
                          <p className="text-xs font-semibold text-text">{plan.name}</p>
                          <p className="text-lg font-bold text-text">${plan.price}/mo</p>
                        </button>
                      ))}
                    </div>
                  </div>

                  <Button
                    type="submit"
                    className="w-full"
                    loading={submitting}
                    size="lg"
                  >
                    Create Agency Account
                  </Button>

                  <p className="text-center text-xs text-text-4">
                    By signing up, you agree to our{" "}
                    <Link href="/terms" className="text-navy hover:underline">Terms</Link>
                    {" "}and{" "}
                    <Link href="/privacy" className="text-navy hover:underline">Privacy Policy</Link>
                  </p>
                </CardBody>
              </Card>
            </form>
          )}
        </div>
      </section>

      {/* Footer CTA */}
      <section className="border-t border-border bg-navy px-4 py-16 text-white">
        <div className="mx-auto max-w-3xl text-center">
          <h2 className="text-2xl font-bold sm:text-3xl">
            Ready to grow your business?
          </h2>
          <p className="mt-3 text-blue-100">
            Join agencies already earning recurring revenue with HireAI white-label.
          </p>
          <div className="mt-6 flex items-center justify-center gap-4">
            <a href="#signup">
              <Button
                size="lg"
                className="bg-white text-navy hover:bg-blue-50"
              >
                Start Free Trial
              </Button>
            </a>
            <Link href="/contact">
              <Button
                variant="outline"
                size="lg"
                className="border-white/30 text-white hover:bg-white/10"
              >
                Contact Sales
              </Button>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
