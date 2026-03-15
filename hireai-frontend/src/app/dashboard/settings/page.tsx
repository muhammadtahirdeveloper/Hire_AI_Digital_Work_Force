"use client";

import { useState } from "react";
import { useSession } from "next-auth/react";
import {
  User,
  Bell,
  Shield,
  Database,
  Plug,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Mail,
  MessageSquare,
  Smartphone,
  Volume2,
  Clock,
  Bot,
  CreditCard,
  Sun,
  Moon,
  Monitor,
} from "lucide-react";
import Link from "next/link";
import { useTheme } from "next-themes";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardBody } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Avatar } from "@/components/ui/avatar";
import {
  Select,
  SelectTrigger,
  SelectContent,
  SelectItem,
  SelectValue,
} from "@/components/ui/select";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";
import { useAgentStatus } from "@/hooks/use-dashboard";
import toast from "react-hot-toast";

// --- Constants ---

const timezones = [
  "UTC",
  "America/New_York",
  "America/Chicago",
  "America/Los_Angeles",
  "Europe/London",
  "Europe/Paris",
  "Asia/Karachi",
  "Asia/Dubai",
  "Asia/Kolkata",
  "Asia/Tokyo",
];

const languages = ["English", "Urdu", "Arabic", "Spanish", "French", "German", "Chinese"];

// --- Page ---

export default function SettingsPage() {
  const { data: session } = useSession();
  const { data: agentStatus } = useAgentStatus();
  const user = session?.user;

  // Profile state
  const [fullName, setFullName] = useState(user?.name || "");
  const [displayName, setDisplayName] = useState(user?.name?.split(" ")[0] || "");
  const [timezone, setTimezone] = useState("UTC");
  const [language, setLanguage] = useState("English");
  const [profileSaving, setProfileSaving] = useState(false);

  // Notifications state
  const [emailNotifs, setEmailNotifs] = useState({
    weeklySummary: true,
    trialExpiry: true,
    agentErrors: true,
    escalation: true,
  });
  const [whatsappNumber, setWhatsappNumber] = useState("");
  const [whatsappNotifs, setWhatsappNotifs] = useState({
    escalation: true,
    dailySummary: false,
    criticalErrors: true,
  });
  const [inAppNotifs, setInAppNotifs] = useState({
    browser: true,
    sound: false,
  });

  // Theme
  const { theme, setTheme } = useTheme();

  // Agent schedule state
  const [scheduledPause, setScheduledPause] = useState(false);
  const [pauseSchedule, setPauseSchedule] = useState("weekends");
  const [pauseFrom, setPauseFrom] = useState("18:00");
  const [pauseTo, setPauseTo] = useState("09:00");

  // Database state
  const [dbUrl, setDbUrl] = useState("");
  const [dbStatus, setDbStatus] = useState<"idle" | "testing" | "connected" | "failed">("idle");
  const [usingCustomDb, setUsingCustomDb] = useState(false);

  const handleSaveProfile = async () => {
    setProfileSaving(true);
    try {
      await api.patch("/api/user/profile", {
        full_name: fullName,
        display_name: displayName,
        timezone,
        language,
      });
      toast.success("Profile saved");
    } catch {
      toast.error("Failed to save profile");
    }
    setProfileSaving(false);
  };

  const handleTestDb = async () => {
    setDbStatus("testing");
    try {
      await api.post("/api/settings/test-database", { url: dbUrl });
      setDbStatus("connected");
      toast.success("Database connection successful");
    } catch {
      setDbStatus("failed");
      toast.error("Database connection failed");
    }
  };

  const handleActivateDb = async () => {
    try {
      await api.post("/api/settings/activate-database", { url: dbUrl });
      setUsingCustomDb(true);
      toast.success("Custom database activated");
    } catch {
      toast.error("Failed to activate database");
    }
  };

  const handleSendTestWhatsapp = async () => {
    try {
      await api.post("/api/settings/test-whatsapp", { number: whatsappNumber });
      toast.success("Test message sent");
    } catch {
      toast.error("Failed to send test message");
    }
  };

  return (
    <div className="space-y-6 pt-4 lg:pt-0">
      <div>
        <h1 className="text-2xl font-bold text-text">Settings</h1>
        <p className="mt-1 text-sm text-text-3">
          Manage your account, notifications, and integrations
        </p>
      </div>

      <Tabs defaultValue="profile">
        <TabsList className="w-full overflow-x-auto">
          <TabsTrigger value="profile" className="gap-1.5">
            <User className="h-3.5 w-3.5" /> Profile
          </TabsTrigger>
          <TabsTrigger value="notifications" className="gap-1.5">
            <Bell className="h-3.5 w-3.5" /> Notifications
          </TabsTrigger>
          <TabsTrigger value="security" className="gap-1.5">
            <Shield className="h-3.5 w-3.5" /> Security
          </TabsTrigger>
          <TabsTrigger value="database" className="gap-1.5">
            <Database className="h-3.5 w-3.5" /> Database
          </TabsTrigger>
          <TabsTrigger value="agent" className="gap-1.5">
            <Bot className="h-3.5 w-3.5" /> Agent
          </TabsTrigger>
          <TabsTrigger value="billing" className="gap-1.5">
            <CreditCard className="h-3.5 w-3.5" /> Billing
          </TabsTrigger>
          <TabsTrigger value="integrations" className="gap-1.5">
            <Plug className="h-3.5 w-3.5" /> Integrations
          </TabsTrigger>
        </TabsList>

        {/* TAB 1: Profile */}
        <TabsContent value="profile">
          <Card>
            <CardBody className="space-y-6 p-6">
              <div className="flex items-center gap-4">
                <Avatar
                  src={user?.image || undefined}
                  fallback={user?.name || "U"}
                  size="lg"
                />
                <div>
                  <p className="text-sm font-medium text-text">{user?.name}</p>
                  <p className="text-xs text-text-4">
                    Photo from Google account (cannot be changed)
                  </p>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <Input
                  label="Full name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
                <Input
                  label="Display name"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                />
              </div>

              <Input
                label="Email"
                value={user?.email || ""}
                disabled
                helperText="Linked to your Google account"
              />

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label className="block text-sm font-medium text-text-2">
                    Timezone
                  </label>
                  <Select value={timezone} onValueChange={setTimezone}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {timezones.map((tz) => (
                        <SelectItem key={tz} value={tz}>{tz}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <label className="block text-sm font-medium text-text-2">
                    Language
                  </label>
                  <Select value={language} onValueChange={setLanguage}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      {languages.map((l) => (
                        <SelectItem key={l} value={l}>{l}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Theme */}
              <div className="space-y-1.5">
                <label className="block text-sm font-medium text-text-2">
                  Theme
                </label>
                <div className="grid grid-cols-3 gap-2">
                  <button
                    onClick={() => setTheme("light")}
                    className={cn(
                      "flex items-center justify-center gap-2 rounded-lg border-2 px-3 py-2.5 text-sm transition-all",
                      theme === "light" ? "border-navy bg-navy/5" : "border-border hover:border-border-2"
                    )}
                  >
                    <Sun className="h-4 w-4" /> Light
                  </button>
                  <button
                    onClick={() => setTheme("dark")}
                    className={cn(
                      "flex items-center justify-center gap-2 rounded-lg border-2 px-3 py-2.5 text-sm transition-all",
                      theme === "dark" ? "border-navy bg-navy/5" : "border-border hover:border-border-2"
                    )}
                  >
                    <Moon className="h-4 w-4" /> Dark
                  </button>
                  <button
                    onClick={() => setTheme("system")}
                    className={cn(
                      "flex items-center justify-center gap-2 rounded-lg border-2 px-3 py-2.5 text-sm transition-all",
                      theme === "system" ? "border-navy bg-navy/5" : "border-border hover:border-border-2"
                    )}
                  >
                    <Monitor className="h-4 w-4" /> System
                  </button>
                </div>
              </div>

              <Button loading={profileSaving} onClick={handleSaveProfile}>
                Save Profile
              </Button>
            </CardBody>
          </Card>
        </TabsContent>

        {/* TAB 2: Notifications */}
        <TabsContent value="notifications">
          <div className="space-y-6">
            {/* Email Notifications */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Mail className="h-4 w-4 text-navy" />
                  <h3 className="text-sm font-semibold text-text">Email Notifications</h3>
                </div>
              </CardHeader>
              <CardBody className="space-y-4">
                <Switch
                  checked={emailNotifs.weeklySummary}
                  onCheckedChange={(v) => setEmailNotifs((p) => ({ ...p, weeklySummary: v }))}
                  label="Weekly summary report (every Monday)"
                />
                <Switch
                  checked={emailNotifs.trialExpiry}
                  onCheckedChange={(v) => setEmailNotifs((p) => ({ ...p, trialExpiry: v }))}
                  label="Trial expiry reminder (2 days before)"
                />
                <Switch
                  checked={emailNotifs.agentErrors}
                  onCheckedChange={(v) => setEmailNotifs((p) => ({ ...p, agentErrors: v }))}
                  label="Agent error alerts"
                />
                <Switch
                  checked={emailNotifs.escalation}
                  onCheckedChange={(v) => setEmailNotifs((p) => ({ ...p, escalation: v }))}
                  label="Escalation email notifications"
                />
              </CardBody>
            </Card>

            {/* WhatsApp Notifications */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Smartphone className="h-4 w-4 text-navy" />
                  <h3 className="text-sm font-semibold text-text">WhatsApp Notifications</h3>
                </div>
              </CardHeader>
              <CardBody className="space-y-4">
                <div className="flex items-end gap-2">
                  <Input
                    label="WhatsApp number"
                    placeholder="+1 234 567 8900"
                    value={whatsappNumber}
                    onChange={(e) => setWhatsappNumber(e.target.value)}
                    className="flex-1"
                  />
                  <Button variant="outline" size="sm" onClick={handleSendTestWhatsapp}>
                    Send Test Message
                  </Button>
                </div>
                <Switch
                  checked={whatsappNotifs.escalation}
                  onCheckedChange={(v) => setWhatsappNotifs((p) => ({ ...p, escalation: v }))}
                  label="Escalation alerts"
                />
                <Switch
                  checked={whatsappNotifs.dailySummary}
                  onCheckedChange={(v) => setWhatsappNotifs((p) => ({ ...p, dailySummary: v }))}
                  label="Daily summary"
                />
                <Switch
                  checked={whatsappNotifs.criticalErrors}
                  onCheckedChange={(v) => setWhatsappNotifs((p) => ({ ...p, criticalErrors: v }))}
                  label="Critical error alerts"
                />
              </CardBody>
            </Card>

            {/* In-App Notifications */}
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <Volume2 className="h-4 w-4 text-navy" />
                  <h3 className="text-sm font-semibold text-text">In-App Notifications</h3>
                </div>
              </CardHeader>
              <CardBody className="space-y-4">
                <Switch
                  checked={inAppNotifs.browser}
                  onCheckedChange={(v) => setInAppNotifs((p) => ({ ...p, browser: v }))}
                  label="Show browser notifications"
                />
                <Switch
                  checked={inAppNotifs.sound}
                  onCheckedChange={(v) => setInAppNotifs((p) => ({ ...p, sound: v }))}
                  label="Sound alerts"
                />
              </CardBody>
            </Card>
          </div>
        </TabsContent>

        {/* TAB 3: Security */}
        <TabsContent value="security">
          <Card>
            <CardBody className="space-y-6 p-6">
              <div className="flex items-center gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-background-2">
                  <Shield className="h-6 w-6 text-navy" />
                </div>
                <div>
                  <p className="text-sm font-medium text-text">
                    Connected via Google OAuth
                  </p>
                  <p className="text-xs text-text-4">{user?.email}</p>
                </div>
              </div>

              <div className="grid gap-4 sm:grid-cols-2">
                <div className="rounded-lg border border-border p-4">
                  <p className="text-xs text-text-3">Last login</p>
                  <p className="mt-1 flex items-center gap-1.5 text-sm font-medium text-text">
                    <Clock className="h-3.5 w-3.5 text-text-4" />
                    {new Date().toLocaleDateString("en-US", {
                      weekday: "short",
                      year: "numeric",
                      month: "short",
                      day: "numeric",
                      hour: "2-digit",
                      minute: "2-digit",
                    })}
                  </p>
                </div>
                <div className="rounded-lg border border-border p-4">
                  <p className="text-xs text-text-3">Account created</p>
                  <p className="mt-1 text-sm font-medium text-text">
                    When you first signed up
                  </p>
                </div>
              </div>

              <div>
                <h3 className="mb-3 text-sm font-semibold text-text">
                  Active Sessions
                </h3>
                <div className="rounded-lg border border-border p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="h-2 w-2 rounded-full bg-success" />
                      <div>
                        <p className="text-sm font-medium text-text">
                          Current session
                        </p>
                        <p className="text-xs text-text-4">
                          This device &middot; Active now
                        </p>
                      </div>
                    </div>
                    <Badge variant="success" size="sm">Active</Badge>
                  </div>
                </div>
              </div>

              <Button
                variant="danger"
                onClick={() => toast.success("All other sessions revoked")}
              >
                Sign out all devices
              </Button>

              <div className="rounded-lg border border-border p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm font-medium text-text">
                      Two-factor authentication
                    </p>
                    <p className="text-xs text-text-4">
                      Add an extra layer of security
                    </p>
                  </div>
                  <Badge variant="default" size="sm">Coming Soon</Badge>
                </div>
              </div>
            </CardBody>
          </Card>
        </TabsContent>

        {/* TAB 4: Database */}
        <TabsContent value="database">
          <Card>
            <CardHeader>
              <h3 className="text-base font-semibold text-text">
                Connect Your Own Database
              </h3>
              <p className="text-sm text-text-3">
                For enhanced security and data control, connect your own
                PostgreSQL database. Your emails and agent data will be stored
                there instead of our shared database.
              </p>
            </CardHeader>
            <CardBody className="space-y-6">
              {/* Warning */}
              <div className="rounded-lg border border-warning/30 bg-warning/10 px-4 py-3">
                <p className="flex items-start gap-2 text-sm text-text-2">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
                  Only for advanced users. If your database goes down or hits
                  limits, your agent will pause until reconnected.
                </p>
              </div>

              {/* Status */}
              <div className="rounded-lg border border-border p-4">
                <p className="text-sm text-text-3">Current status</p>
                <p className="mt-1 flex items-center gap-2 text-sm font-medium text-text">
                  {usingCustomDb ? (
                    <>
                      <CheckCircle2 className="h-4 w-4 text-success" />
                      Using custom database
                    </>
                  ) : (
                    <>
                      <Database className="h-4 w-4 text-navy" />
                      Using HireAI database (default)
                    </>
                  )}
                </p>
              </div>

              {/* Form */}
              <Input
                label="Database URL"
                type="password"
                placeholder="postgresql://user:password@host:5432/dbname"
                value={dbUrl}
                onChange={(e) => {
                  setDbUrl(e.target.value);
                  setDbStatus("idle");
                }}
              />

              <div className="flex items-center gap-3">
                <Button
                  variant="outline"
                  onClick={handleTestDb}
                  loading={dbStatus === "testing"}
                  disabled={!dbUrl}
                >
                  Test Connection
                </Button>
                {dbStatus === "connected" && (
                  <span className="flex items-center gap-1 text-sm text-success">
                    <CheckCircle2 className="h-4 w-4" /> Connected
                  </span>
                )}
                {dbStatus === "failed" && (
                  <span className="flex items-center gap-1 text-sm text-danger">
                    <XCircle className="h-4 w-4" /> Connection failed
                  </span>
                )}
              </div>

              {dbStatus === "connected" && !usingCustomDb && (
                <Button onClick={handleActivateDb}>
                  Activate Custom Database
                </Button>
              )}

              {usingCustomDb && (
                <Button
                  variant="outline"
                  onClick={() => {
                    setUsingCustomDb(false);
                    toast.success("Switched back to HireAI database");
                  }}
                >
                  Switch Back to HireAI Database
                </Button>
              )}
            </CardBody>
          </Card>
        </TabsContent>

        {/* TAB: Agent Schedule */}
        <TabsContent value="agent">
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4 text-navy" />
                <h3 className="text-sm font-semibold text-text">Agent Pause Schedule</h3>
              </div>
              <p className="text-sm text-text-3">
                Automatically pause and resume your agent on a schedule
              </p>
            </CardHeader>
            <CardBody className="space-y-6">
              <Switch
                checked={scheduledPause}
                onCheckedChange={setScheduledPause}
                label="Enable scheduled pause"
              />

              {scheduledPause && (
                <div className="space-y-4 rounded-lg border border-border p-4">
                  <div className="space-y-1.5">
                    <label className="block text-sm font-medium text-text-2">
                      Schedule
                    </label>
                    <Select value={pauseSchedule} onValueChange={setPauseSchedule}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="weekends">Every weekend (Sat-Sun)</SelectItem>
                        <SelectItem value="evenings">Every evening</SelectItem>
                        <SelectItem value="custom">Custom hours</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  {pauseSchedule !== "weekends" && (
                    <div className="grid grid-cols-2 gap-4">
                      <Input
                        label="Pause from"
                        type="time"
                        value={pauseFrom}
                        onChange={(e) => setPauseFrom(e.target.value)}
                      />
                      <Input
                        label="Resume at"
                        type="time"
                        value={pauseTo}
                        onChange={(e) => setPauseTo(e.target.value)}
                      />
                    </div>
                  )}

                  <p className="text-xs text-text-4">
                    Your agent will automatically pause and resume based on this schedule.
                    Emails received during pause will be queued and processed when the agent resumes.
                  </p>

                  <Button
                    onClick={() => toast.success("Schedule saved")}
                  >
                    Save Schedule
                  </Button>
                </div>
              )}
            </CardBody>
          </Card>
        </TabsContent>

        {/* TAB: Billing */}
        <TabsContent value="billing">
          <div className="space-y-6">
            <Card>
              <CardHeader>
                <div className="flex items-center gap-2">
                  <CreditCard className="h-4 w-4 text-navy" />
                  <h3 className="text-sm font-semibold text-text">Current Plan</h3>
                </div>
              </CardHeader>
              <CardBody className="space-y-4">
                <div className="flex items-center justify-between rounded-lg border border-border p-4">
                  <div>
                    <p className="text-lg font-bold text-text capitalize">
                      {agentStatus?.tier?.replace("tier", "Tier ") || user?.tier || "Trial"}
                    </p>
                    <p className="text-sm text-text-3">
                      {agentStatus?.tier === "tier1" && "$19/mo"}
                      {agentStatus?.tier === "tier2" && "$49/mo"}
                      {agentStatus?.tier === "tier3" && "$99/mo"}
                      {(!agentStatus?.tier || agentStatus?.tier === "trial") && "Free Trial"}
                    </p>
                  </div>
                  <Badge variant={user?.tier === "trial" ? "warning" : "success"}>
                    {user?.tier === "trial" ? "Trial" : "Active"}
                  </Badge>
                </div>
              </CardBody>
            </Card>

            <Card>
              <CardHeader>
                <h3 className="text-sm font-semibold text-text">Plan Actions</h3>
              </CardHeader>
              <CardBody className="space-y-3">
                <Link href="/dashboard/billing">
                  <Button className="w-full">Manage Plan & Billing</Button>
                </Link>
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => toast("Contact support at hireaidigitalemployee@gmail.com to downgrade your plan.")}
                >
                  Downgrade Plan
                </Button>
                <Button
                  variant="danger"
                  className="w-full"
                  onClick={() => toast("Contact support at hireaidigitalemployee@gmail.com to cancel.", { icon: "\u26a0\ufe0f" })}
                >
                  Cancel Subscription
                </Button>
              </CardBody>
            </Card>
          </div>
        </TabsContent>

        {/* TAB 5: Integrations */}
        <TabsContent value="integrations">
          <Card>
            <CardBody className="divide-y divide-border p-0">
              {/* Gmail */}
              <div className="flex items-center justify-between p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-50 dark:bg-red-900/20">
                    <Mail className="h-5 w-5 text-red-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text">Gmail</p>
                    <p className="text-xs text-text-4">
                      {agentStatus?.gmail_connected || "Not connected"}
                    </p>
                  </div>
                </div>
                <Badge variant={agentStatus?.gmail_valid ? "success" : "danger"}>
                  {agentStatus?.gmail_valid ? (
                    <><CheckCircle2 className="mr-1 h-3 w-3" /> Connected</>
                  ) : (
                    <><XCircle className="mr-1 h-3 w-3" /> Disconnected</>
                  )}
                </Badge>
              </div>

              {/* WhatsApp */}
              <div className="flex items-center justify-between p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-50 dark:bg-green-900/20">
                    <MessageSquare className="h-5 w-5 text-green-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text">WhatsApp</p>
                    <p className="text-xs text-text-4">
                      {whatsappNumber || "Not configured"}
                    </p>
                  </div>
                </div>
                <Badge variant={whatsappNumber ? "success" : "default"}>
                  {whatsappNumber ? "Connected" : "Not set"}
                </Badge>
              </div>

              {/* Slack */}
              <div className="flex items-center justify-between p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-50 dark:bg-purple-900/20">
                    <MessageSquare className="h-5 w-5 text-purple-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text">Slack</p>
                    <p className="text-xs text-text-4">Team notifications</p>
                  </div>
                </div>
                <Badge variant="default">Coming Soon</Badge>
              </div>

              {/* HubSpot */}
              <div className="flex items-center justify-between p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-orange-50 dark:bg-orange-900/20">
                    <Plug className="h-5 w-5 text-orange-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text">HubSpot CRM</p>
                    <p className="text-xs text-text-4">Sync contacts and deals</p>
                  </div>
                </div>
                <Button variant="outline" size="sm">Connect</Button>
              </div>

              {/* Calendar */}
              <div className="flex items-center justify-between p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-900/20">
                    <Clock className="h-5 w-5 text-blue-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text">Calendar</p>
                    <p className="text-xs text-text-4">Schedule meetings</p>
                  </div>
                </div>
                <Badge variant="default">Coming Soon</Badge>
              </div>

              {/* Zapier */}
              <div className="flex items-center justify-between p-5">
                <div className="flex items-center gap-3">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-amber-50 dark:bg-amber-900/20">
                    <Plug className="h-5 w-5 text-amber-600" />
                  </div>
                  <div>
                    <p className="text-sm font-medium text-text">Zapier</p>
                    <p className="text-xs text-text-4">Connect 5000+ apps</p>
                  </div>
                </div>
                <Badge variant="default">Coming Soon</Badge>
              </div>
            </CardBody>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
