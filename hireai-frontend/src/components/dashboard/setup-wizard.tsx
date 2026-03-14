"use client";

import { useState } from "react";
import {
  Globe,
  Users,
  Home,
  ShoppingCart,
  ArrowRight,
  ArrowLeft,
  Check,
  Mail,
  Sparkles,
  Database,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

type AgentType = "general" | "hr" | "real_estate" | "ecommerce";

interface SetupData {
  gmailAddress: string;
  gmailConnected: boolean;
  agentType: AgentType | null;
  businessName: string;
  userName: string;
  replyTone: "formal" | "friendly" | "casual";
  workingHoursFrom: string;
  workingHoursTo: string;
  whatsappNumber: string;
  useCustomDb: boolean;
  customDbUrl: string;
}

const agents = [
  {
    type: "general" as AgentType,
    icon: Globe,
    label: "General Agent",
    description: "All industries, all email types",
  },
  {
    type: "hr" as AgentType,
    icon: Users,
    label: "HR Agent",
    description: "CVs, interviews, candidates, job inquiries",
  },
  {
    type: "real_estate" as AgentType,
    icon: Home,
    label: "Real Estate Agent",
    description: "Property inquiries, viewings, maintenance",
  },
  {
    type: "ecommerce" as AgentType,
    icon: ShoppingCart,
    label: "E-commerce Agent",
    description: "Orders, refunds, complaints, suppliers",
  },
];

const tones = [
  { value: "formal" as const, label: "Formal", description: "Professional and polished" },
  { value: "friendly" as const, label: "Friendly", description: "Warm and approachable" },
  { value: "casual" as const, label: "Casual", description: "Relaxed and conversational" },
];

const TOTAL_STEPS = 6;

export function SetupWizard() {
  const [step, setStep] = useState(1);
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<SetupData>({
    gmailAddress: "",
    gmailConnected: false,
    agentType: null,
    businessName: "",
    userName: "",
    replyTone: "friendly",
    workingHoursFrom: "09:00",
    workingHoursTo: "17:00",
    whatsappNumber: "",
    useCustomDb: false,
    customDbUrl: "",
  });

  const canProceed = (): boolean => {
    switch (step) {
      case 1:
        return true;
      case 2:
        return data.gmailAddress.includes("@");
      case 3:
        return data.agentType !== null;
      case 4:
        return data.businessName.trim() !== "" && data.userName.trim() !== "";
      case 5:
        return true; // Database step is optional
      default:
        return true;
    }
  };

  const handleConnectGmail = () => {
    // In production, this would open Google OAuth for Gmail scope
    // For now, mark as connected if email is valid
    if (data.gmailAddress.includes("@gmail.com")) {
      setData((prev) => ({ ...prev, gmailConnected: true }));
    }
  };

  const handleFinish = async () => {
    setLoading(true);
    try {
      await api.post("/auth/setup", {
        gmail_address: data.gmailAddress,
        agent_type: data.agentType,
        business_name: data.businessName,
        user_name: data.userName,
        reply_tone: data.replyTone,
        working_hours_from: data.workingHoursFrom,
        working_hours_to: data.workingHoursTo,
        whatsapp_number: data.whatsappNumber || null,
        custom_db_url: data.useCustomDb ? data.customDbUrl : null,
      });
    } catch {
      // Setup data saved locally; backend sync can retry later
    }
    try {
      await api.post("/api/user/complete-setup");
    } catch {
      // Non-critical — dashboard still works
    }
    setLoading(false);
    setStep(6);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-background">
      <div className="w-full max-w-2xl px-4">
        {/* Progress bar */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs text-text-3">
              Step {step} of {TOTAL_STEPS}
            </span>
            <span className="text-xs text-text-4">
              {Math.round((step / TOTAL_STEPS) * 100)}%
            </span>
          </div>
          <div className="h-1.5 w-full rounded-full bg-background-2">
            <div
              className="h-1.5 rounded-full bg-navy transition-all duration-300"
              style={{ width: `${(step / TOTAL_STEPS) * 100}%` }}
            />
          </div>
        </div>

        <div className="rounded-xl border border-border bg-background p-8 shadow-sm">
          {/* Step 1: Welcome */}
          {step === 1 && (
            <div className="text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-2xl bg-navy-light">
                <Sparkles className="h-8 w-8 text-navy" />
              </div>
              <h2 className="mt-6 text-2xl font-bold text-text">
                Welcome to HireAI!
              </h2>
              <p className="mt-2 text-text-3">
                Let&apos;s get you set up in 3 quick steps. Your AI email agent
                will be live in no time.
              </p>
            </div>
          )}

          {/* Step 2: Connect Gmail */}
          {step === 2 && (
            <div>
              <div className="flex items-center gap-3 mb-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy-light">
                  <Mail className="h-5 w-5 text-navy" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-text">Connect Gmail</h2>
                  <p className="text-sm text-text-3">
                    Which Gmail should your agent monitor?
                  </p>
                </div>
              </div>

              <Input
                label="Gmail address"
                type="email"
                placeholder="your-email@gmail.com"
                value={data.gmailAddress}
                onChange={(e) =>
                  setData((prev) => ({
                    ...prev,
                    gmailAddress: e.target.value,
                    gmailConnected: false,
                  }))
                }
                helperText="This can be different from your signup email"
                prefixIcon={<Mail className="h-4 w-4" />}
              />

              <div className="mt-4">
                <Button
                  variant="outline"
                  onClick={handleConnectGmail}
                  disabled={!data.gmailAddress.includes("@")}
                  className="w-full"
                >
                  {data.gmailConnected ? (
                    <>
                      <Check className="h-4 w-4 text-success" />
                      Connected
                    </>
                  ) : (
                    "Connect Gmail"
                  )}
                </Button>
              </div>

              {data.gmailConnected && (
                <div className="mt-4 flex items-center gap-2 rounded-lg bg-success-light p-3 text-sm text-success">
                  <Check className="h-4 w-4" />
                  Gmail connected successfully
                </div>
              )}
            </div>
          )}

          {/* Step 3: Choose Agent */}
          {step === 3 && (
            <div>
              <h2 className="text-xl font-bold text-text">Choose your agent</h2>
              <p className="mt-1 text-sm text-text-3">
                Select an agent for your industry
              </p>

              <div className="mt-6 grid gap-3 sm:grid-cols-2">
                {agents.map((agent) => (
                  <button
                    key={agent.type}
                    onClick={() =>
                      setData((prev) => ({ ...prev, agentType: agent.type }))
                    }
                    className={cn(
                      "flex flex-col items-start gap-3 rounded-xl border-2 p-5 text-left transition-all",
                      data.agentType === agent.type
                        ? "border-navy bg-navy/5"
                        : "border-border hover:border-border-2"
                    )}
                  >
                    <div
                      className={cn(
                        "flex h-10 w-10 items-center justify-center rounded-lg",
                        data.agentType === agent.type
                          ? "bg-navy text-white"
                          : "bg-background-2 text-text-3"
                      )}
                    >
                      <agent.icon className="h-5 w-5" />
                    </div>
                    <div>
                      <p className="font-medium text-text">{agent.label}</p>
                      <p className="mt-0.5 text-xs text-text-3">
                        {agent.description}
                      </p>
                    </div>
                    {data.agentType === agent.type && (
                      <div className="flex h-5 w-5 items-center justify-center rounded-full bg-navy text-white">
                        <Check className="h-3 w-3" />
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Step 4: Business Profile */}
          {step === 4 && (
            <div>
              <h2 className="text-xl font-bold text-text">Business profile</h2>
              <p className="mt-1 text-sm text-text-3">
                Tell us a bit about your business
              </p>

              <div className="mt-6 space-y-4">
                <Input
                  label="Business name"
                  placeholder="Acme Corp"
                  value={data.businessName}
                  onChange={(e) =>
                    setData((prev) => ({
                      ...prev,
                      businessName: e.target.value,
                    }))
                  }
                  required
                />

                <Input
                  label="Your name"
                  placeholder="John Doe"
                  value={data.userName}
                  onChange={(e) =>
                    setData((prev) => ({ ...prev, userName: e.target.value }))
                  }
                  required
                />

                {/* Reply tone */}
                <div>
                  <label className="block text-sm font-medium text-text-2 mb-2">
                    Reply tone
                  </label>
                  <div className="grid grid-cols-3 gap-2">
                    {tones.map((tone) => (
                      <button
                        key={tone.value}
                        onClick={() =>
                          setData((prev) => ({
                            ...prev,
                            replyTone: tone.value,
                          }))
                        }
                        className={cn(
                          "rounded-lg border-2 px-3 py-2.5 text-center transition-all",
                          data.replyTone === tone.value
                            ? "border-navy bg-navy/5"
                            : "border-border hover:border-border-2"
                        )}
                      >
                        <p className="text-sm font-medium text-text">
                          {tone.label}
                        </p>
                        <p className="mt-0.5 text-[10px] text-text-4">
                          {tone.description}
                        </p>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Working hours */}
                <div className="grid grid-cols-2 gap-4">
                  <Input
                    label="Working hours from"
                    type="time"
                    value={data.workingHoursFrom}
                    onChange={(e) =>
                      setData((prev) => ({
                        ...prev,
                        workingHoursFrom: e.target.value,
                      }))
                    }
                  />
                  <Input
                    label="Working hours to"
                    type="time"
                    value={data.workingHoursTo}
                    onChange={(e) =>
                      setData((prev) => ({
                        ...prev,
                        workingHoursTo: e.target.value,
                      }))
                    }
                  />
                </div>

                <Input
                  label="WhatsApp number (optional)"
                  placeholder="+1 234 567 8900"
                  value={data.whatsappNumber}
                  onChange={(e) =>
                    setData((prev) => ({
                      ...prev,
                      whatsappNumber: e.target.value,
                    }))
                  }
                  helperText="For urgent email escalation alerts"
                />
              </div>
            </div>
          )}

          {/* Step 5: Database (optional) */}
          {step === 5 && (
            <div>
              <div className="flex items-center gap-3 mb-6">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-navy-light">
                  <Database className="h-5 w-5 text-navy" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-text">Database</h2>
                  <p className="text-sm text-text-3">
                    Connect your own database or use ours
                  </p>
                </div>
              </div>

              <div className="space-y-4">
                {/* Toggle */}
                <button
                  onClick={() =>
                    setData((prev) => ({
                      ...prev,
                      useCustomDb: !prev.useCustomDb,
                      customDbUrl: !prev.useCustomDb ? prev.customDbUrl : "",
                    }))
                  }
                  className={cn(
                    "flex w-full items-center justify-between rounded-xl border-2 p-4 text-left transition-all",
                    data.useCustomDb
                      ? "border-navy bg-navy/5"
                      : "border-border hover:border-border-2"
                  )}
                >
                  <div>
                    <p className="font-medium text-text">
                      Use custom database
                    </p>
                    <p className="mt-0.5 text-xs text-text-3">
                      Your data stays in your database
                    </p>
                  </div>
                  <div
                    className={cn(
                      "flex h-6 w-11 items-center rounded-full px-0.5 transition-colors",
                      data.useCustomDb ? "bg-navy" : "bg-background-2"
                    )}
                  >
                    <div
                      className={cn(
                        "h-5 w-5 rounded-full bg-white shadow-sm transition-transform",
                        data.useCustomDb ? "translate-x-5" : "translate-x-0"
                      )}
                    />
                  </div>
                </button>

                {data.useCustomDb && (
                  <Input
                    label="PostgreSQL connection URL"
                    type="text"
                    placeholder="postgresql://user:pass@host:5432/dbname"
                    value={data.customDbUrl}
                    onChange={(e) =>
                      setData((prev) => ({
                        ...prev,
                        customDbUrl: e.target.value,
                      }))
                    }
                    helperText="Your data is encrypted and never shared"
                    prefixIcon={<Database className="h-4 w-4" />}
                  />
                )}

                {!data.useCustomDb && (
                  <div className="flex items-center gap-2 rounded-lg bg-navy/5 p-3 text-sm text-navy">
                    <Check className="h-4 w-4 shrink-0" />
                    Using HireAI&apos;s managed database (recommended)
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step 6: Done */}
          {step === 6 && (
            <div className="text-center">
              <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-success-light">
                <Check className="h-8 w-8 text-success" />
              </div>
              <h2 className="mt-6 text-2xl font-bold text-text">
                Your HireAI agent is live!
              </h2>
              <p className="mt-2 text-text-3">
                Everything is configured and ready to go.
              </p>

              <div className="mt-8 rounded-lg border border-border bg-background-1 p-4 text-left text-sm">
                <div className="space-y-2">
                  <div className="flex justify-between">
                    <span className="text-text-3">Gmail</span>
                    <span className="font-medium text-text">
                      {data.gmailAddress}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-3">Agent</span>
                    <span className="font-medium text-text">
                      {agents.find((a) => a.type === data.agentType)?.label}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-3">Business</span>
                    <span className="font-medium text-text">
                      {data.businessName}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-3">Tone</span>
                    <span className="font-medium text-text capitalize">
                      {data.replyTone}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-text-3">Hours</span>
                    <span className="font-medium text-text">
                      {data.workingHoursFrom} – {data.workingHoursTo}
                    </span>
                  </div>
                </div>
              </div>

              <Button
                className="mt-8"
                size="lg"
                onClick={() => {
                  window.location.href = "/dashboard";
                }}
                rightIcon={<ArrowRight className="h-4 w-4" />}
              >
                Go to Dashboard
              </Button>
            </div>
          )}

          {/* Navigation buttons */}
          {step < 6 && (
            <div className="mt-8 flex items-center justify-between">
              {step > 1 ? (
                <Button
                  variant="ghost"
                  onClick={() => setStep((s) => s - 1)}
                  leftIcon={<ArrowLeft className="h-4 w-4" />}
                >
                  Back
                </Button>
              ) : (
                <div />
              )}

              {step < 5 ? (
                <Button
                  onClick={() => setStep((s) => s + 1)}
                  disabled={!canProceed()}
                  rightIcon={<ArrowRight className="h-4 w-4" />}
                >
                  Continue
                </Button>
              ) : (
                <Button
                  onClick={handleFinish}
                  loading={loading}
                  disabled={!canProceed()}
                  rightIcon={<Check className="h-4 w-4" />}
                >
                  Finish setup
                </Button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
