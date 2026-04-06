"use client";

import { useState, useEffect } from "react";
import { useAuth } from "@/hooks/use-auth";
import {
  Globe,
  Users,
  Home,
  ShoppingCart,
  Check,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Mail,
  Clock,
  Target,
  BellOff,
  Bell,
  FlaskConical,
  Trash2,
  Pause,
  RotateCcw,
  Lock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardBody } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import {
  Modal,
  ModalTrigger,
  ModalContent,
  ModalHeader,
  ModalTitle,
  ModalDescription,
  ModalFooter,
} from "@/components/ui/modal";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useAgentStatus, useProviderHealth } from "@/hooks/use-dashboard";
import toast from "react-hot-toast";

// --- Data ---

type AgentType = "general" | "hr" | "real_estate" | "ecommerce";

const agentCards = [
  {
    type: "general" as AgentType,
    icon: Globe,
    label: "General Agent",
    description: "Handles all types of emails across any industry",
    bestFor: "Small businesses, freelancers",
  },
  {
    type: "hr" as AgentType,
    icon: Users,
    label: "HR Agent",
    description: "CVs, interview scheduling, candidate follow-ups, job inquiries",
    bestFor: "HR teams, recruitment agencies",
  },
  {
    type: "real_estate" as AgentType,
    icon: Home,
    label: "Real Estate Agent",
    description: "Property inquiries, viewing requests, maintenance, lease renewals",
    bestFor: "Real estate agencies, property managers",
  },
  {
    type: "ecommerce" as AgentType,
    icon: ShoppingCart,
    label: "E-commerce Agent",
    description: "Order inquiries, refunds, complaints, shipping, supplier emails",
    bestFor: "Online stores, e-commerce businesses",
  },
];

const tierCards = [
  {
    id: "tier1",
    name: "Starter",
    price: 9,
    model: "Claude Haiku (Fast)",
    popular: false,
  },
  {
    id: "tier2",
    name: "Professional",
    price: 29,
    model: "Claude Haiku",
    popular: true,
  },
  {
    id: "tier3",
    name: "Enterprise",
    price: 59,
    model: "Claude Sonnet 4.5",
    popular: false,
    note: "or $39/mo with BYOK",
  },
];

function getModelForTier(tier: string): { name: string; provider: string } {
  switch (tier) {
    case "tier2":
    case "professional":
      return { name: "Claude Haiku", provider: "Anthropic" };
    case "tier3":
    case "enterprise":
      return { name: "Claude Sonnet 4.5", provider: "Anthropic" };
    default:
      // trial, starter, tier1
      return { name: "Claude Haiku (Fast)", provider: "Anthropic" };
  }
}

const modelDescriptions: Record<string, string> = {
  "Claude Haiku (Fast)": "Fast and efficient for routine email classification and quick replies. Great for high-volume processing.",
  "Claude Haiku": "Fast and efficient for routine email classification and quick replies. Great for high-volume processing.",
  "Claude Sonnet 4.5": "Advanced reasoning for complex emails, nuanced replies, and accurate classification across all categories.",
};

const languages = [
  "Auto (Match Email)",
  "English",
  "Urdu",
  "Arabic",
  "Hindi",
  "Spanish",
  "French",
  "German",
  "Chinese",
];

const timezones = [
  { value: "Asia/Karachi", label: "Pakistan Standard Time (PKT, UTC+5)" },
  { value: "UTC", label: "UTC" },
  { value: "America/New_York", label: "Eastern Time (ET, UTC-5)" },
  { value: "America/Chicago", label: "Central Time (CT, UTC-6)" },
  { value: "America/Denver", label: "Mountain Time (MT, UTC-7)" },
  { value: "America/Los_Angeles", label: "Pacific Time (PT, UTC-8)" },
  { value: "Europe/London", label: "London (GMT, UTC+0)" },
  { value: "Europe/Paris", label: "Paris (CET, UTC+1)" },
  { value: "Asia/Dubai", label: "Dubai (GST, UTC+4)" },
  { value: "Asia/Kolkata", label: "India (IST, UTC+5:30)" },
  { value: "Asia/Shanghai", label: "China (CST, UTC+8)" },
  { value: "Asia/Tokyo", label: "Tokyo (JST, UTC+9)" },
  { value: "Australia/Sydney", label: "Sydney (AEST, UTC+10)" },
];

const defaultCategories = [
  { name: "CV Applications", autoReply: true, escalate: false },
  { name: "Interview Requests", autoReply: true, escalate: true },
  { name: "Offer Letters", autoReply: false, escalate: true },
  { name: "Follow-ups", autoReply: true, escalate: false },
  { name: "Newsletters", autoReply: false, escalate: false },
  { name: "Spam", autoReply: false, escalate: false },
  { name: "Complaints", autoReply: true, escalate: true },
  { name: "Leads", autoReply: true, escalate: false },
  { name: "General", autoReply: true, escalate: false },
];

const weekdays = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

// --- Config State ---

interface AgentConfig {
  businessName: string;
  userName: string;
  businessDescription: string;
  replyLanguage: string;
  replyTone: string;
  workingHoursEnabled: boolean;
  workingHoursFrom: string;
  workingHoursTo: string;
  workingDays: boolean[];
  timezone: string;
  queueOutsideHours: boolean;
  categories: typeof defaultCategories;
  blacklist: string;
  whitelist: string;
  blockedKeywords: string;
  whatsappNumber: string;
  escalationKeywords: string;
  escalationEmail: string;
  testMode: boolean;
  autoSend: boolean;
  maxEmailsPerDay: number;
  reviewHighPriority: boolean;
}

// --- Page ---

export default function AgentManagementPage() {
  const { session } = useAuth();
  const { data: agentStatus, mutate: mutateAgent } = useAgentStatus();
  const { data: providerHealth } = useProviderHealth();
  const [switchModalOpen, setSwitchModalOpen] = useState(false);
  const [pendingAgent, setPendingAgent] = useState<AgentType | null>(null);
  const [tierModalOpen, setTierModalOpen] = useState(false);
  const [pendingTier, setPendingTier] = useState<string | null>(null);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const currentAgent = (agentStatus?.agent_type || session?.user?.agentType || "general") as AgentType;
  const currentTier = agentStatus?.tier || session?.user?.tier || "trial";
  const tierModel = getModelForTier(currentTier);
  const currentModel = tierModel.name;

  const [config, setConfig] = useState<AgentConfig>({
    businessName: "",
    userName: "",
    businessDescription: "",
    replyLanguage: "Auto (Match Email)",
    replyTone: "friendly",
    workingHoursEnabled: true,
    workingHoursFrom: "09:00",
    workingHoursTo: "17:00",
    workingDays: [true, true, true, true, true, false, false],
    timezone: "Asia/Karachi",
    queueOutsideHours: true,
    categories: defaultCategories,
    blacklist: "",
    whitelist: "",
    blockedKeywords: "",
    whatsappNumber: "",
    escalationKeywords: "",
    escalationEmail: "",
    testMode: agentStatus?.test_mode ?? false,
    autoSend: agentStatus?.tier === "tier2" || agentStatus?.tier === "tier3",
    maxEmailsPerDay: 100,
    reviewHighPriority: true,
  });

  useEffect(() => {
    if (agentStatus) {
      setConfig((prev) => ({ ...prev, testMode: agentStatus.test_mode }));
    }
  }, [agentStatus]);

  // Load existing config from backend on mount
  useEffect(() => {
    api
      .get("/api/agent/config")
      .then((res) => {
        const cfg = res.data?.data ?? res.data;
        if (cfg && typeof cfg === "object") {
          setConfig((prev) => ({
            ...prev,
            businessName: cfg.business_name ?? cfg.businessName ?? prev.businessName,
            userName: cfg.user_name ?? cfg.userName ?? prev.userName,
            businessDescription: cfg.business_description ?? cfg.businessDescription ?? prev.businessDescription,
            replyLanguage: cfg.reply_language ?? cfg.replyLanguage ?? prev.replyLanguage,
            replyTone: cfg.reply_tone ?? cfg.replyTone ?? prev.replyTone,
            workingHoursFrom: cfg.working_hours_from ?? cfg.working_hours?.from ?? prev.workingHoursFrom,
            workingHoursTo: cfg.working_hours_to ?? cfg.working_hours?.to ?? prev.workingHoursTo,
            timezone: cfg.timezone ?? prev.timezone,
            whatsappNumber: cfg.whatsapp_number ?? cfg.whatsappNumber ?? prev.whatsappNumber,
            blacklist: cfg.blacklist ?? prev.blacklist,
            whitelist: cfg.whitelist ?? prev.whitelist,
            blockedKeywords: cfg.blocked_keywords ?? cfg.blockedKeywords ?? prev.blockedKeywords,
            escalationKeywords: cfg.escalation_keywords ?? cfg.escalationKeywords ?? prev.escalationKeywords,
            escalationEmail: cfg.escalation_email ?? cfg.escalationEmail ?? prev.escalationEmail,
            workingHoursEnabled: cfg.working_hours_enabled ?? cfg.workingHoursEnabled ?? prev.workingHoursEnabled,
            workingDays: cfg.working_days ?? cfg.workingDays ?? prev.workingDays,
            queueOutsideHours: cfg.queue_outside_hours ?? cfg.queueOutsideHours ?? prev.queueOutsideHours,
            categories: cfg.categories ?? prev.categories,
            testMode: cfg.test_mode ?? prev.testMode,
            autoSend: cfg.auto_send ?? cfg.autoSend ?? prev.autoSend,
            maxEmailsPerDay: cfg.max_emails_per_day ?? cfg.maxEmailsPerDay ?? prev.maxEmailsPerDay,
            reviewHighPriority: cfg.review_high_priority ?? cfg.reviewHighPriority ?? prev.reviewHighPriority,
          }));
        }
      })
      .catch(() => {});
  }, []);

  const updateConfig = (partial: Partial<AgentConfig>) => {
    setConfig((prev) => ({ ...prev, ...partial }));
  };

  const handleSwitchAgent = async () => {
    if (!pendingAgent) return;
    try {
      await api.patch("/api/agent/config", { agent_type: pendingAgent });
      mutateAgent();
      toast.success(`Switched to ${agentCards.find((a) => a.type === pendingAgent)?.label}`);
    } catch {
      toast.error("Failed to switch agent");
    }
    setSwitchModalOpen(false);
    setPendingAgent(null);
  };

  const handleSwitchTier = async () => {
    if (!pendingTier) return;
    try {
      await api.patch("/api/agent/config", { tier: pendingTier });
      mutateAgent();
      toast.success("Plan updated");
    } catch {
      toast.error("Failed to update plan");
    }
    setTierModalOpen(false);
    setPendingTier(null);
  };

  const handleSaveConfig = async () => {
    setSaving(true);
    try {
      await api.patch("/api/agent/config", {
        business_name: config.businessName,
        user_name: config.userName,
        business_description: config.businessDescription,
        reply_language: config.replyLanguage,
        reply_tone: config.replyTone,
        working_hours_enabled: config.workingHoursEnabled,
        working_hours_from: config.workingHoursFrom,
        working_hours_to: config.workingHoursTo,
        working_days: config.workingDays,
        timezone: config.timezone,
        queue_outside_hours: config.queueOutsideHours,
        categories: config.categories,
        blacklist: config.blacklist,
        whitelist: config.whitelist,
        blocked_keywords: config.blockedKeywords,
        whatsapp_number: config.whatsappNumber,
        escalation_keywords: config.escalationKeywords,
        escalation_email: config.escalationEmail,
        test_mode: config.testMode,
        auto_send: config.autoSend,
        max_emails_per_day: config.maxEmailsPerDay,
        review_high_priority: config.reviewHighPriority,
      });
      mutateAgent();
      toast.success("Configuration saved");
    } catch {
      toast.error("Failed to save configuration");
    }
    setSaving(false);
  };

  const handlePauseAgent = async () => {
    try {
      await api.post("/api/agent/pause");
      mutateAgent();
      toast.success("Agent paused");
    } catch {
      toast.error("Failed to pause agent");
    }
  };

  const handleResumeAgent = async () => {
    try {
      await api.post("/api/agent/resume");
      mutateAgent();
      toast.success("Agent resumed");
    } catch {
      toast.error("Failed to resume agent");
    }
  };

  const handleResetAgent = async () => {
    try {
      await api.post("/api/agent/reset");
      mutateAgent();
      toast.success("Agent preferences reset");
    } catch {
      toast.error("Failed to reset agent");
    }
  };

  // Listen for Gmail OAuth popup callback
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.data?.type === "gmail-connected") {
        mutateAgent();
        toast.success("Gmail account connected successfully");
      }
    };
    window.addEventListener("message", handler);
    return () => window.removeEventListener("message", handler);
  }, [mutateAgent]);

  const handleChangeGmail = () => {
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
    const email = session?.user?.email || "";
    const oauthUrl = `${backendUrl}/auth/google?setup=true&email=${encodeURIComponent(email)}`;
    window.open(oauthUrl, "_blank", "width=500,height=600");
  };

  return (
    <div className="space-y-8 pt-4 lg:pt-0">
      <div>
        <h1 className="text-2xl font-bold text-text">Agent Management</h1>
        <p className="mt-1 text-sm text-text-3">
          Configure your AI agent, plan, and email processing settings
        </p>
      </div>

      {/* 1. AGENT SELECTOR */}
      <section>
        <h2 className="text-lg font-semibold text-text mb-4">Your Active Agent</h2>
        <div className="grid gap-4 sm:grid-cols-2">
          {agentCards.map((agent) => {
            const isActive = agent.type === currentAgent;
            return (
              <button
                key={agent.type}
                onClick={() => {
                  if (!isActive) {
                    setPendingAgent(agent.type);
                    setSwitchModalOpen(true);
                  }
                }}
                className={cn(
                  "relative flex flex-col items-start gap-3 rounded-xl border-2 p-6 text-left transition-all",
                  isActive
                    ? "border-navy bg-navy/5"
                    : "border-border hover:border-border-2 hover:shadow-sm"
                )}
              >
                {isActive && (
                  <Badge variant="navy" className="absolute right-4 top-4">
                    <Check className="mr-1 h-3 w-3" /> Active
                  </Badge>
                )}
                <div
                  className={cn(
                    "flex h-12 w-12 items-center justify-center rounded-xl",
                    isActive ? "bg-navy text-white" : "bg-background-2 text-text-3"
                  )}
                >
                  <agent.icon className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-base font-semibold text-text">{agent.label}</p>
                  <p className="mt-1 text-sm text-text-3">{agent.description}</p>
                  <p className="mt-2 text-xs text-text-4">
                    Best for: {agent.bestFor}
                  </p>
                </div>
              </button>
            );
          })}
        </div>

        {/* Switch Agent Modal */}
        <Modal open={switchModalOpen} onOpenChange={setSwitchModalOpen}>
          <ModalContent>
            <ModalHeader>
              <ModalTitle>Switch Agent?</ModalTitle>
              <ModalDescription>
                Switching agent will change how your emails are processed. Are
                you sure? Your email history will be preserved.
              </ModalDescription>
            </ModalHeader>
            <ModalFooter>
              <Button variant="ghost" onClick={() => setSwitchModalOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSwitchAgent}>Confirm Switch</Button>
            </ModalFooter>
          </ModalContent>
        </Modal>
      </section>

      {/* 2. TIER SELECTOR */}
      <section>
        <h2 className="text-lg font-semibold text-text mb-4">Your Current Plan</h2>
        <div className="grid gap-4 md:grid-cols-3">
          {tierCards.map((tier) => {
            const isActive = tier.id === currentTier;
            return (
              <button
                key={tier.id}
                onClick={() => {
                  if (!isActive) {
                    setPendingTier(tier.id);
                    setTierModalOpen(true);
                  }
                }}
                className={cn(
                  "relative flex flex-col rounded-xl border-2 p-6 text-left transition-all",
                  isActive
                    ? "border-navy bg-navy/5"
                    : "border-border hover:border-border-2"
                )}
              >
                {tier.popular && (
                  <Badge variant="navy" className="absolute -top-2.5 right-4">
                    Most Popular
                  </Badge>
                )}
                <p className="text-base font-semibold text-text">{tier.name}</p>
                <p className="mt-2 text-3xl font-bold text-text">
                  ${tier.price}
                  <span className="text-sm font-normal text-text-3">/mo</span>
                </p>
                <p className="mt-1 font-mono text-xs text-text-4">{tier.model}</p>
                {"note" in tier && tier.note && (
                  <p className="mt-0.5 text-xs text-navy">{tier.note}</p>
                )}
                {isActive && (
                  <Badge variant="success" className="mt-3">
                    Current Plan
                  </Badge>
                )}
              </button>
            );
          })}
        </div>
        <p className="mt-3 text-xs text-text-4">
          Next billing date: Change plan before your renewal to take effect.
        </p>

        {/* Tier Switch Modal */}
        <Modal open={tierModalOpen} onOpenChange={setTierModalOpen}>
          <ModalContent>
            <ModalHeader>
              <ModalTitle>Change Plan?</ModalTitle>
              <ModalDescription>
                {pendingTier && tierCards.find((t) => t.id === pendingTier)
                  ? `Switch to ${tierCards.find((t) => t.id === pendingTier)?.name} ($${tierCards.find((t) => t.id === pendingTier)?.price}/mo)?`
                  : "Confirm plan change?"}
                {" "}Changes take effect at your next billing cycle.
              </ModalDescription>
            </ModalHeader>
            <ModalFooter>
              <Button variant="ghost" onClick={() => setTierModalOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleSwitchTier}>Confirm Change</Button>
            </ModalFooter>
          </ModalContent>
        </Modal>
      </section>

      {/* 3. AI MODEL INFO */}
      <Card>
        <CardBody className="p-6">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-navy-light">
              <Cpu className="h-6 w-6 text-navy" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-text">AI Model</h3>
              <p className="mt-1 font-mono text-lg text-navy">{currentModel}</p>
              <p className="mt-2 text-sm text-text-3">
                {modelDescriptions[currentModel] ||
                  "Your agent uses this model for processing emails."}
              </p>
            </div>
          </div>
        </CardBody>
      </Card>

      {/* 3b. PROVIDER HEALTH */}
      <Card>
        <CardBody className="p-6">
          <div className="flex items-start gap-4">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-background-2">
              <span
                className={cn(
                  "h-4 w-4 rounded-full",
                  providerHealth?.status === "healthy"
                    ? "bg-success"
                    : providerHealth?.status === "error"
                    ? "bg-danger"
                    : "bg-text-4"
                )}
              />
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-2">
                <h3 className="text-base font-semibold text-text">AI Provider</h3>
                <Badge
                  variant={providerHealth?.status === "healthy" ? "success" : "danger"}
                >
                  {providerHealth?.status === "healthy" ? "Healthy" : providerHealth?.status === "error" ? "Error" : "Checking..."}
                </Badge>
              </div>
              <p className="mt-1 text-sm text-text-2">
                Provider:{" "}
                <span className="font-medium capitalize">
                  {providerHealth?.provider || "loading..."}
                </span>
              </p>
              <p className="text-sm text-text-3">
                Model:{" "}
                <span className="font-mono text-xs">
                  {providerHealth?.model || currentModel}
                </span>
              </p>
              {providerHealth?.error && (
                <p className="mt-1 text-xs text-danger">
                  {providerHealth.error} — system will use fallback provider
                </p>
              )}
            </div>
          </div>
        </CardBody>
      </Card>

      {/* 4. AGENT CONFIGURATION */}
      <section className="space-y-6">
        <h2 className="text-lg font-semibold text-text">Configure Your Agent</h2>

        {/* Business Profile */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Mail className="h-4 w-4 text-navy" />
              <h3 className="text-sm font-semibold text-text">Business Profile</h3>
            </div>
          </CardHeader>
          <CardBody className="space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <Input
                label="Business name"
                placeholder="Acme Corp"
                value={config.businessName}
                onChange={(e) => updateConfig({ businessName: e.target.value })}
              />
              <Input
                label="Your name"
                placeholder="John Doe"
                value={config.userName}
                onChange={(e) => updateConfig({ userName: e.target.value })}
              />
            </div>
            <Input
              label="Business description"
              placeholder="Brief description of your business (used in AI prompts)"
              value={config.businessDescription}
              onChange={(e) => updateConfig({ businessDescription: e.target.value })}
            />
            <div className="grid gap-4 sm:grid-cols-2">
              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-text-2">
                  Reply language
                </label>
                <Select
                  value={config.replyLanguage}
                  onValueChange={(v) => updateConfig({ replyLanguage: v })}
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {languages.map((lang) => (
                      <SelectItem key={lang} value={lang}>
                        {lang}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-text-2">
                  Reply tone
                </label>
                <div className="grid grid-cols-2 gap-2">
                  {["formal", "professional", "friendly", "casual"].map((tone) => (
                    <button
                      key={tone}
                      onClick={() => updateConfig({ replyTone: tone })}
                      className={cn(
                        "rounded-lg border px-3 py-2 text-sm capitalize transition-all",
                        config.replyTone === tone
                          ? "border-navy bg-navy/5 text-navy font-medium"
                          : "border-border text-text-3 hover:border-border-2"
                      )}
                    >
                      {tone}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </CardBody>
        </Card>

        {/* Working Hours */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Clock className="h-4 w-4 text-navy" />
                <h3 className="text-sm font-semibold text-text">Working Hours</h3>
              </div>
              <Switch
                checked={config.workingHoursEnabled}
                onCheckedChange={(v) => updateConfig({ workingHoursEnabled: v })}
                label="Restrict to working hours"
              />
            </div>
          </CardHeader>
          {config.workingHoursEnabled && (
            <CardBody className="space-y-4">
              <div className="grid gap-4 sm:grid-cols-3">
                <Input
                  label="From"
                  type="time"
                  value={config.workingHoursFrom}
                  onChange={(e) => updateConfig({ workingHoursFrom: e.target.value })}
                />
                <Input
                  label="To"
                  type="time"
                  value={config.workingHoursTo}
                  onChange={(e) => updateConfig({ workingHoursTo: e.target.value })}
                />
                <div className="space-y-1.5">
                  <label className="block text-sm font-medium text-text-2">
                    Timezone
                  </label>
                  <Select
                    value={config.timezone}
                    onValueChange={(v) => updateConfig({ timezone: v })}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {timezones.map((tz) => (
                        <SelectItem key={tz.value} value={tz.value}>
                          {tz.label}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-text-2">
                  Working days
                </label>
                <div className="flex flex-wrap gap-2">
                  {weekdays.map((day, i) => (
                    <button
                      key={day}
                      onClick={() => {
                        const days = [...config.workingDays];
                        days[i] = !days[i];
                        updateConfig({ workingDays: days });
                      }}
                      className={cn(
                        "rounded-lg border px-3 py-1.5 text-xs font-medium transition-all",
                        config.workingDays[i]
                          ? "border-navy bg-navy text-white"
                          : "border-border text-text-3 hover:border-border-2"
                      )}
                    >
                      {day}
                    </button>
                  ))}
                </div>
              </div>
              <Switch
                checked={config.queueOutsideHours}
                onCheckedChange={(v) => updateConfig({ queueOutsideHours: v })}
                label="Queue emails for next working day"
              />
            </CardBody>
          )}
        </Card>

        {/* Email Priorities */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Target className="h-4 w-4 text-navy" />
              <h3 className="text-sm font-semibold text-text">Email Priorities</h3>
            </div>
          </CardHeader>
          <CardBody>
            <div className="space-y-2">
              <div className="grid grid-cols-3 gap-4 border-b border-border pb-2 text-xs font-medium text-text-3">
                <span>Category</span>
                <span className="text-center">Auto-reply</span>
                <span className="text-center">Escalate</span>
              </div>
              {config.categories.map((cat, i) => (
                <div
                  key={cat.name}
                  className="grid grid-cols-3 items-center gap-4 py-1.5"
                >
                  <span className="text-sm text-text-2">{cat.name}</span>
                  <div className="flex justify-center">
                    <Switch
                      checked={cat.autoReply}
                      onCheckedChange={(v) => {
                        const cats = [...config.categories];
                        cats[i] = { ...cats[i], autoReply: v };
                        updateConfig({ categories: cats });
                      }}
                    />
                  </div>
                  <div className="flex justify-center">
                    <Switch
                      checked={cat.escalate}
                      onCheckedChange={(v) => {
                        const cats = [...config.categories];
                        cats[i] = { ...cats[i], escalate: v };
                        updateConfig({ categories: cats });
                      }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </CardBody>
        </Card>

        {/* Blacklist / Whitelist */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <BellOff className="h-4 w-4 text-navy" />
              <h3 className="text-sm font-semibold text-text">
                Blacklist / Whitelist
              </h3>
            </div>
          </CardHeader>
          <CardBody className="space-y-4">
            <div>
              <label className="mb-1.5 block text-sm font-medium text-text-2">
                Blacklist (never process)
              </label>
              <textarea
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-text placeholder:text-text-4 focus:outline-none focus:ring-2 focus:ring-navy"
                rows={3}
                placeholder="One email per line"
                value={config.blacklist}
                onChange={(e) => updateConfig({ blacklist: e.target.value })}
              />
            </div>
            <div>
              <label className="mb-1.5 block text-sm font-medium text-text-2">
                VIP Whitelist (always prioritize)
              </label>
              <textarea
                className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-text placeholder:text-text-4 focus:outline-none focus:ring-2 focus:ring-navy"
                rows={3}
                placeholder="One email per line"
                value={config.whitelist}
                onChange={(e) => updateConfig({ whitelist: e.target.value })}
              />
            </div>
            <Input
              label="Blocked keywords"
              placeholder="unsubscribe, newsletter, promo"
              value={config.blockedKeywords}
              onChange={(e) => updateConfig({ blockedKeywords: e.target.value })}
              helperText="Subject keywords to automatically archive (comma-separated)"
            />
          </CardBody>
        </Card>

        {/* Escalation Settings */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Bell className="h-4 w-4 text-navy" />
              <h3 className="text-sm font-semibold text-text">
                Escalation Settings
              </h3>
            </div>
          </CardHeader>
          <CardBody className="space-y-4">
            <Input
              label="WhatsApp number"
              placeholder="+1 234 567 8900"
              value={config.whatsappNumber}
              onChange={(e) => updateConfig({ whatsappNumber: e.target.value })}
              helperText="Receive escalation alerts via WhatsApp"
            />
            <Input
              label="Escalation keywords"
              placeholder="urgent, lawsuit, CEO, deadline"
              value={config.escalationKeywords}
              onChange={(e) =>
                updateConfig({ escalationKeywords: e.target.value })
              }
              helperText="Emails containing these keywords will be escalated (comma-separated)"
            />
            <Input
              label="Escalation email"
              placeholder="manager@company.com"
              value={config.escalationEmail}
              onChange={(e) =>
                updateConfig({ escalationEmail: e.target.value })
              }
              helperText="Forward escalated emails to this address (can be different from main)"
            />
          </CardBody>
        </Card>

        {/* Agent Behavior */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <FlaskConical className="h-4 w-4 text-navy" />
              <h3 className="text-sm font-semibold text-text">Agent Behavior</h3>
            </div>
          </CardHeader>
          <CardBody className="space-y-5">
            <Switch
              checked={config.testMode}
              onCheckedChange={(v) => updateConfig({ testMode: v })}
              label="Test Mode — Agent only creates drafts, never sends"
            />
            <Switch
              checked={config.autoSend}
              onCheckedChange={async (v) => {
                updateConfig({ autoSend: v });
                try {
                  await api.patch("/api/agent/config", { auto_send: v });
                  toast.success(v ? "Auto-send enabled — agent will send replies automatically" : "Auto-send disabled — agent will create drafts only");
                } catch {
                  toast.error("Failed to update auto-send setting");
                }
              }}
              label={config.autoSend
                ? "Auto-send ON — Agent will send replies automatically"
                : "Auto-send OFF — Agent will create drafts only"}
            />
            <div>
              <label className="mb-1.5 block text-sm font-medium text-text-2">
                Max emails per day: {config.maxEmailsPerDay}
              </label>
              <input
                type="range"
                min={10}
                max={500}
                step={10}
                value={config.maxEmailsPerDay}
                onChange={(e) =>
                  updateConfig({ maxEmailsPerDay: Number(e.target.value) })
                }
                className="w-full accent-navy"
              />
              <div className="flex justify-between text-xs text-text-4">
                <span>10</span>
                <span>500</span>
              </div>
            </div>
            <Switch
              checked={config.reviewHighPriority}
              onCheckedChange={(v) => updateConfig({ reviewHighPriority: v })}
              label="Review before send for high-priority emails"
            />
          </CardBody>
        </Card>

        {/* Save Button */}
        <Button
          className="w-full"
          size="lg"
          loading={saving}
          onClick={handleSaveConfig}
        >
          Save Configuration
        </Button>
      </section>

      {/* 5. GMAIL CONNECTION */}
      <section>
        <h2 className="text-lg font-semibold text-text mb-4">
          Connected Gmail Accounts
        </h2>
        <Card>
          <CardBody className="space-y-4 p-6">
            {/* Main Gmail */}
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-full bg-background-2">
                  <Mail className="h-5 w-5 text-text-3" />
                </div>
                <div>
                  <p className="text-sm font-medium text-text">
                    {agentStatus?.gmail_connected
                      ? agentStatus.gmail_connected
                      : "No Gmail connected"}
                  </p>
                  <p className="text-xs text-text-4">
                    {agentStatus?.gmail_connected
                      ? "Monitoring Gmail"
                      : "Connect a Gmail account to start"}
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {agentStatus?.gmail_connected ? (
                  <Badge variant="success">
                    <CheckCircle2 className="mr-1 h-3 w-3" /> Connected
                  </Badge>
                ) : (
                  <Badge variant="danger">
                    <AlertTriangle className="mr-1 h-3 w-3" /> Not Connected
                  </Badge>
                )}
                <Button variant="outline" size="sm" onClick={handleChangeGmail}>
                  {agentStatus?.gmail_connected ? "Change Gmail" : "Connect Gmail"}
                </Button>
              </div>
            </div>

            <hr className="border-border" />

            {/* Reply-from Gmail */}
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-text">
                  Reply-from Gmail
                </p>
                <p className="text-xs text-text-4">
                  Agent can reply from a different Gmail (Tier 2+)
                </p>
              </div>
              {currentTier === "tier1" || currentTier === "trial" ? (
                <div className="flex items-center gap-2 text-xs text-text-4">
                  <Lock className="h-3.5 w-3.5" />
                  <span>Upgrade to unlock</span>
                </div>
              ) : (
                <Button variant="outline" size="sm">
                  Connect Gmail
                </Button>
              )}
            </div>
          </CardBody>
        </Card>
      </section>

      {/* 6. DANGER ZONE */}
      <section>
        <h2 className="text-lg font-semibold text-text mb-4">Danger Zone</h2>
        <Card className="border-danger/30">
          <CardBody className="space-y-4 p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-text">
                  {agentStatus?.is_paused ? "Resume Agent" : "Pause Agent"}
                </p>
                <p className="text-xs text-text-3">
                  {agentStatus?.is_paused
                    ? "Agent is paused. Click to resume processing emails."
                    : "Stops processing emails. You can resume anytime."}
                </p>
              </div>
              {agentStatus?.is_paused ? (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleResumeAgent}
                  leftIcon={<RotateCcw className="h-4 w-4" />}
                >
                  Resume
                </Button>
              ) : (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handlePauseAgent}
                  leftIcon={<Pause className="h-4 w-4" />}
                >
                  Pause
                </Button>
              )}
            </div>

            <hr className="border-border" />

            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-text">Reset Agent</p>
                <p className="text-xs text-text-3">
                  Clears all learned preferences and resets to defaults.
                </p>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleResetAgent}
                leftIcon={<RotateCcw className="h-4 w-4" />}
              >
                Reset
              </Button>
            </div>

            <hr className="border-border" />

            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-danger">Delete Account</p>
                <p className="text-xs text-text-3">
                  Permanently delete your account and all data.
                </p>
              </div>
              <Modal open={deleteModalOpen} onOpenChange={setDeleteModalOpen}>
                <ModalTrigger asChild>
                  <Button
                    variant="danger"
                    size="sm"
                    leftIcon={<Trash2 className="h-4 w-4" />}
                  >
                    Delete
                  </Button>
                </ModalTrigger>
                <ModalContent>
                  <ModalHeader>
                    <ModalTitle>Delete Account?</ModalTitle>
                    <ModalDescription>
                      This will permanently delete your account, agent
                      configuration, and all email history. This action cannot
                      be undone.
                    </ModalDescription>
                  </ModalHeader>
                  <ModalFooter>
                    <Button
                      variant="ghost"
                      onClick={() => setDeleteModalOpen(false)}
                    >
                      Cancel
                    </Button>
                    <Button
                      variant="danger"
                      onClick={async () => {
                        try {
                          await api.delete("/api/account");
                          toast.success("Account deleted");
                          setDeleteModalOpen(false);
                          // Clear all session/auth data
                          localStorage.clear();
                          sessionStorage.clear();
                          document.cookie.split(";").forEach((c) => {
                            document.cookie = c.replace(/^ +/, "").replace(/=.*/, "=;expires=" + new Date().toUTCString() + ";path=/");
                          });
                          window.location.href = "/";
                        } catch {
                          toast.error("Failed to delete account");
                        }
                      }}
                    >
                      Delete Account
                    </Button>
                  </ModalFooter>
                </ModalContent>
              </Modal>
            </div>
          </CardBody>
        </Card>
      </section>
    </div>
  );
}
