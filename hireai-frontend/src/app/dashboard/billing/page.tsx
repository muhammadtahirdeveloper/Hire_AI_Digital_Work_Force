"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import {
  Check,
  CreditCard,
  Copy,
  Gift,
  FileText,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardBody } from "@/components/ui/card";
import {
  Modal,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalFooter,
} from "@/components/ui/modal";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useAgentStatus } from "@/hooks/use-dashboard";
import toast from "react-hot-toast";

// --- Data ---

const plans = [
  {
    id: "tier1",
    name: "Starter",
    price: 19,
    model: "claude-haiku-3-5",
    popular: false,
    features: [
      "500 emails/month",
      "1 Gmail account",
      "Smart classification",
      "Auto reply drafts",
      "Basic analytics",
    ],
  },
  {
    id: "tier2",
    name: "Professional",
    price: 49,
    model: "claude-sonnet-4-5",
    popular: true,
    features: [
      "5,000 emails/month",
      "3 Gmail accounts",
      "All Starter features",
      "Custom rules engine",
      "WhatsApp escalation",
      "Priority support",
    ],
  },
  {
    id: "tier3",
    name: "Enterprise",
    price: 99,
    model: "claude-sonnet-4-5",
    popular: false,
    features: [
      "Unlimited emails",
      "10 Gmail accounts",
      "All Professional features",
      "Advanced analytics",
      "Custom agent training",
      "Dedicated support",
    ],
  },
];

const billingHistory = [
  { date: "2025-03-01", plan: "Professional", amount: "$49.00", status: "Paid", invoice: "#INV-003" },
  { date: "2025-02-01", plan: "Professional", amount: "$49.00", status: "Paid", invoice: "#INV-002" },
  { date: "2025-01-01", plan: "Starter", amount: "$19.00", status: "Paid", invoice: "#INV-001" },
];

function getTrialDaysLeft(trialEndDate?: string): number {
  if (!trialEndDate) return 0;
  const diff = new Date(trialEndDate).getTime() - Date.now();
  return Math.max(0, Math.ceil(diff / (1000 * 60 * 60 * 24)));
}

// --- Page ---

export default function BillingPage() {
  const { data: session } = useSession();
  const { data: agentStatus, mutate: mutateAgent } = useAgentStatus();
  const [planModalOpen, setPlanModalOpen] = useState(false);
  const [cancelModalOpen, setCancelModalOpen] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState<string | null>(null);

  const user = session?.user;
  const currentTier = agentStatus?.tier || user?.tier || "trial";
  const currentModel = agentStatus?.model || "claude-sonnet-4-5";
  const isTrial = currentTier === "trial";
  const trialDays = getTrialDaysLeft(user?.trialEndDate);
  const currentPlan = plans.find((p) => p.id === currentTier);
  const referralCode = user?.id ? `HIRE-${user.id.slice(0, 6).toUpperCase()}` : "HIRE-XXXXXX";

  const handleChangePlan = async () => {
    if (!selectedPlan) return;
    try {
      await api.patch("/api/agent/config", { tier: selectedPlan });
      mutateAgent();
      toast.success("Plan updated successfully");
    } catch {
      toast.error("Failed to update plan");
    }
    setPlanModalOpen(false);
    setSelectedPlan(null);
  };

  const handleCancel = async () => {
    try {
      await api.post("/api/billing/cancel");
      toast.success("Subscription cancelled. Agent active until period end.");
    } catch {
      toast.error("Failed to cancel subscription");
    }
    setCancelModalOpen(false);
  };

  const handleCopyReferral = () => {
    navigator.clipboard.writeText(`https://hireai.com/signup?ref=${referralCode}`);
    toast.success("Referral link copied");
  };

  return (
    <div className="space-y-6 pt-4 lg:pt-0">
      <div>
        <h1 className="text-2xl font-bold text-text">Billing</h1>
        <p className="mt-1 text-sm text-text-3">
          Manage your subscription, plan, and payment
        </p>
      </div>

      {/* 1. CURRENT PLAN CARD */}
      <Card>
        <CardBody className="p-6">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs text-text-3">Current Plan</p>
              <p className="mt-1 text-xl font-bold text-text">
                {isTrial ? "Free Trial" : currentPlan?.name || currentTier}
              </p>
              <div className="mt-2 flex flex-wrap items-center gap-3">
                {!isTrial && currentPlan && (
                  <span className="text-2xl font-bold text-text">
                    ${currentPlan.price}
                    <span className="text-sm font-normal text-text-3">/mo</span>
                  </span>
                )}
                <Badge variant={isTrial ? "warning" : "success"}>
                  {isTrial ? "Trial" : "Active"}
                </Badge>
              </div>
              <p className="mt-2 font-mono text-xs text-text-4">
                {currentModel}
              </p>
              {!isTrial && (
                <p className="mt-1 text-xs text-text-4">
                  Next billing date: {new Date(Date.now() + 30 * 86400000).toLocaleDateString()}
                </p>
              )}
            </div>
            <Button onClick={() => setPlanModalOpen(true)}>
              Change Plan
            </Button>
          </div>
        </CardBody>
      </Card>

      {/* 2. TRIAL STATUS */}
      {isTrial && (
        <Card className="border-warning/30 bg-warning/5">
          <CardBody className="p-6">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h3 className="text-lg font-bold text-text">
                  Free Trial — {trialDays} days remaining
                </h3>
                <p className="mt-1 text-sm text-text-3">
                  After trial ends, choose a plan to keep your agent running.
                </p>
                <ul className="mt-3 space-y-1 text-sm text-text-2">
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-success" /> All agent types available
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-success" /> Full analytics dashboard
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-success" /> claude-sonnet-4-5 model
                  </li>
                  <li className="flex items-center gap-2">
                    <Check className="h-3.5 w-3.5 text-success" /> Up to 100 emails
                  </li>
                </ul>
              </div>
              <Button onClick={() => setPlanModalOpen(true)} size="lg">
                Upgrade Now
              </Button>
            </div>
          </CardBody>
        </Card>
      )}

      {/* 3. PLAN SELECTOR MODAL */}
      <Modal open={planModalOpen} onOpenChange={setPlanModalOpen}>
        <ModalContent className="max-w-3xl">
          <ModalHeader>
            <ModalTitle>Choose a Plan</ModalTitle>
            <ModalDescription>
              Select the plan that fits your needs. Changes take effect immediately.
            </ModalDescription>
          </ModalHeader>
          <div className="grid gap-4 p-6 pt-0 md:grid-cols-3">
            {plans.map((plan) => (
              <button
                key={plan.id}
                onClick={() => setSelectedPlan(plan.id)}
                className={cn(
                  "relative flex flex-col rounded-xl border-2 p-5 text-left transition-all",
                  selectedPlan === plan.id
                    ? "border-navy bg-navy/5"
                    : plan.id === currentTier
                      ? "border-border-2 bg-background-1"
                      : "border-border hover:border-border-2"
                )}
              >
                {plan.popular && (
                  <Badge variant="navy" className="absolute -top-2.5 right-3 text-[10px]">
                    Most Popular
                  </Badge>
                )}
                <p className="font-semibold text-text">{plan.name}</p>
                <p className="mt-2 text-2xl font-bold text-text">
                  ${plan.price}<span className="text-xs font-normal text-text-3">/mo</span>
                </p>
                <p className="mt-1 font-mono text-[10px] text-text-4">{plan.model}</p>
                <ul className="mt-4 flex-1 space-y-1.5">
                  {plan.features.map((f) => (
                    <li key={f} className="flex items-start gap-1.5 text-xs text-text-2">
                      <Check className="mt-0.5 h-3 w-3 shrink-0 text-success" />
                      {f}
                    </li>
                  ))}
                </ul>
                {plan.id === currentTier && (
                  <Badge variant="default" className="mt-3">Current</Badge>
                )}
              </button>
            ))}
          </div>
          <ModalFooter className="px-6 pb-6">
            <Button variant="ghost" onClick={() => setPlanModalOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleChangePlan}
              disabled={!selectedPlan || selectedPlan === currentTier}
            >
              Confirm Change
            </Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      {/* 4. PLAN CHANGE RULES */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <FileText className="h-4 w-4 text-navy" />
            <h3 className="text-sm font-semibold text-text">Plan Change Policy</h3>
          </div>
        </CardHeader>
        <CardBody>
          <ul className="space-y-2 text-sm text-text-2">
            <li className="flex items-start gap-2">
              <span className="mt-1 text-text-4">&bull;</span>
              You can change your plan anytime before your next billing date
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-1 text-text-4">&bull;</span>
              Changes take effect immediately
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-1 text-text-4">&bull;</span>
              Once your subscription renews, plan is locked for that billing period
            </li>
            <li className="flex items-start gap-2">
              <span className="mt-1 text-text-4">&bull;</span>
              You can cancel anytime — agent pauses at end of period
            </li>
          </ul>
        </CardBody>
      </Card>

      {/* 5. PAYMENT METHOD */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <CreditCard className="h-4 w-4 text-navy" />
            <h3 className="text-sm font-semibold text-text">Payment Method</h3>
          </div>
        </CardHeader>
        <CardBody>
          <div className="rounded-lg border border-border bg-background-1 p-4 text-center">
            <p className="text-sm text-text-2">
              Payment integration coming soon. Contact us to arrange payment.
            </p>
            <a
              href="mailto:hireaidigitalemployee@gmail.com"
              className="mt-2 inline-block text-sm font-medium text-navy hover:underline"
            >
              hireaidigitalemployee@gmail.com
            </a>
          </div>
        </CardBody>
      </Card>

      {/* 6. BILLING HISTORY */}
      <Card>
        <CardHeader>
          <h3 className="text-sm font-semibold text-text">Billing History</h3>
        </CardHeader>
        <CardBody className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-xs font-medium text-text-3">
                  <th className="px-4 py-3">Date</th>
                  <th className="px-4 py-3">Plan</th>
                  <th className="px-4 py-3">Amount</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Invoice</th>
                </tr>
              </thead>
              <tbody>
                {billingHistory.map((row) => (
                  <tr
                    key={row.invoice}
                    className="border-b border-border last:border-0 hover:bg-background-1"
                  >
                    <td className="px-4 py-3 text-text-2">{row.date}</td>
                    <td className="px-4 py-3 font-medium text-text">{row.plan}</td>
                    <td className="px-4 py-3 text-text-2">{row.amount}</td>
                    <td className="px-4 py-3">
                      <Badge variant="success" size="sm">{row.status}</Badge>
                    </td>
                    <td className="px-4 py-3 text-text-4">{row.invoice}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardBody>
      </Card>

      {/* 7. CANCEL SUBSCRIPTION */}
      {!isTrial && (
        <div className="text-center">
          <button
            onClick={() => setCancelModalOpen(true)}
            className="text-sm text-text-4 underline hover:text-danger"
          >
            Cancel subscription
          </button>

          <Modal open={cancelModalOpen} onOpenChange={setCancelModalOpen}>
            <ModalContent>
              <ModalHeader>
                <ModalTitle>Cancel Subscription?</ModalTitle>
                <ModalDescription>
                  Your agent will continue until the end of your current billing
                  period. After that, it will pause until you resubscribe.
                </ModalDescription>
              </ModalHeader>
              <ModalFooter>
                <Button onClick={() => setCancelModalOpen(false)}>
                  Keep Subscription
                </Button>
                <Button variant="danger" onClick={handleCancel}>
                  Confirm Cancel
                </Button>
              </ModalFooter>
            </ModalContent>
          </Modal>
        </div>
      )}

      {/* 8. REFERRAL SECTION */}
      <Card className="border-navy/20 bg-gradient-to-r from-navy/5 to-transparent">
        <CardBody className="p-6">
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-navy-light">
              <Gift className="h-5 w-5 text-navy" />
            </div>
            <div className="flex-1">
              <p className="font-semibold text-text">
                Refer a friend, get 1 month free
              </p>
              <p className="mt-1 text-sm text-text-3">
                Share your referral link and earn free months when friends sign up.
              </p>

              <div className="mt-4 flex items-center gap-2">
                <div className="flex-1 rounded-lg border border-border bg-background px-3 py-2 font-mono text-xs text-text-2">
                  https://hireai.com/signup?ref={referralCode}
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopyReferral}
                  leftIcon={<Copy className="h-3.5 w-3.5" />}
                >
                  Copy
                </Button>
              </div>

              <div className="mt-4 flex gap-6 text-sm">
                <div>
                  <p className="text-text-3">Referrals made</p>
                  <p className="text-lg font-bold text-text">0</p>
                </div>
                <div>
                  <p className="text-text-3">Months earned</p>
                  <p className="text-lg font-bold text-text">0</p>
                </div>
              </div>
            </div>
          </div>
        </CardBody>
      </Card>
    </div>
  );
}
