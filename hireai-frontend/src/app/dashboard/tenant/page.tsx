"use client";

import { useState } from "react";
import {
  Users,
  Mail,
  Trash2,
  BarChart3,
  Building2,
  UserPlus,
  Palette,
} from "lucide-react";
import useSWR from "swr";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardHeader, CardBody } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useTenant } from "@/lib/tenant";
import { api } from "@/lib/api";
import toast from "react-hot-toast";

const fetcher = (url: string) => api.get(url).then((r) => r.data?.data ?? r.data);

// --- Types ---

interface TenantUser {
  id: string;
  email: string;
  name: string;
  role: string;
  tier: string;
  created_at: string;
  emails_30d: number;
}

interface TenantStats {
  total_users: number;
  emails_this_month: number;
  tenant_name: string;
  plan: string;
  max_users: number;
  created_at: string;
  user_stats: {
    id: string;
    email: string;
    name: string;
    emails_month: number;
    emails_today: number;
  }[];
}

// --- Page ---

export default function TenantAdminPage() {
  const { brandName, tenant } = useTenant();
  const { data: usersRes, mutate: mutateUsers } = useSWR("/api/tenant/users", fetcher);
  const { data: statsRes } = useSWR("/api/tenant/stats", fetcher);

  const [showInvite, setShowInvite] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteName, setInviteName] = useState("");
  const [inviteRole, setInviteRole] = useState("user");
  const [inviting, setInviting] = useState(false);

  // Branding state
  const [brandingName, setBrandingName] = useState(tenant.brand_name || "");
  const [primaryColor, setPrimaryColor] = useState(tenant.primary_color || "#2563eb");
  const [logoUrl, setLogoUrl] = useState(tenant.logo_url || "");
  const [savingBrand, setSavingBrand] = useState(false);

  const users: TenantUser[] = usersRes?.data || [];
  const stats: TenantStats | null = statsRes?.data || null;

  const handleInvite = async () => {
    if (!inviteEmail) return;
    setInviting(true);
    try {
      await api.post("/api/tenant/users", {
        email: inviteEmail,
        name: inviteName,
        role: inviteRole,
      });
      toast.success(`Invited ${inviteEmail}`);
      setInviteEmail("");
      setInviteName("");
      setShowInvite(false);
      mutateUsers();
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Failed to invite user";
      toast.error(message);
    }
    setInviting(false);
  };

  const handleRemoveUser = async (userId: string, email: string) => {
    if (!confirm(`Remove ${email} from your organization?`)) return;
    try {
      await api.delete(`/api/tenant/users/${userId}`);
      toast.success(`${email} removed`);
      mutateUsers();
    } catch {
      toast.error("Failed to remove user");
    }
  };

  const handleSaveBranding = async () => {
    if (!tenant.id) {
      toast.error("No tenant configured");
      return;
    }
    setSavingBrand(true);
    try {
      await api.patch(`/api/tenants/${tenant.id}`, {
        brand_name: brandingName,
        primary_color: primaryColor,
        logo_url: logoUrl,
      });
      toast.success("Branding saved! Refresh to see changes.");
    } catch {
      toast.error("Failed to save branding");
    }
    setSavingBrand(false);
  };

  const planLabels: Record<string, string> = {
    agency_starter: "Agency Starter",
    agency_pro: "Agency Pro",
    agency_enterprise: "Agency Enterprise",
  };

  return (
    <div className="space-y-6 pt-4 lg:pt-0">
      <div>
        <h1 className="text-2xl font-bold text-text">
          <Building2 className="mr-2 inline h-6 w-6" />
          {brandName} Admin
        </h1>
        <p className="mt-1 text-sm text-text-3">
          Manage your organization&apos;s users, branding, and usage
        </p>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card hover>
          <CardBody className="p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm text-text-3">Total Users</p>
              <Users className="h-4 w-4 text-text-4" />
            </div>
            <p className="mt-2 text-3xl font-bold text-text">
              {stats?.total_users ?? users.length}
            </p>
            <p className="mt-1 text-xs text-text-4">
              of {stats?.max_users ?? 10} allowed
            </p>
          </CardBody>
        </Card>

        <Card hover>
          <CardBody className="p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm text-text-3">Emails This Month</p>
              <Mail className="h-4 w-4 text-text-4" />
            </div>
            <p className="mt-2 text-3xl font-bold text-text">
              {stats?.emails_this_month ?? 0}
            </p>
            <p className="mt-1 text-xs text-text-4">across all users</p>
          </CardBody>
        </Card>

        <Card hover>
          <CardBody className="p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm text-text-3">Plan</p>
              <BarChart3 className="h-4 w-4 text-text-4" />
            </div>
            <p className="mt-2 text-lg font-bold text-text">
              {planLabels[stats?.plan || ""] || stats?.plan || "Starter"}
            </p>
          </CardBody>
        </Card>

        <Card hover>
          <CardBody className="p-5">
            <div className="flex items-center justify-between">
              <p className="text-sm text-text-3">Subdomain</p>
              <Building2 className="h-4 w-4 text-text-4" />
            </div>
            <p className="mt-2 text-sm font-medium text-navy">
              {tenant.slug ? `${tenant.slug}.hireai.app` : "Not configured"}
            </p>
            {tenant.domain && (
              <p className="mt-1 text-xs text-text-4">{tenant.domain}</p>
            )}
          </CardBody>
        </Card>
      </div>

      {/* Users Table */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="h-4 w-4 text-navy" />
              <h2 className="text-base font-semibold text-text">Users</h2>
              <Badge variant="default">{users.length}</Badge>
            </div>
            <Button
              size="sm"
              leftIcon={<UserPlus className="h-4 w-4" />}
              onClick={() => setShowInvite(!showInvite)}
            >
              Add User
            </Button>
          </div>
        </CardHeader>
        <CardBody>
          {/* Invite Form */}
          {showInvite && (
            <div className="mb-4 rounded-lg border border-border p-4">
              <h3 className="mb-3 text-sm font-semibold text-text">Invite User</h3>
              <div className="grid gap-3 sm:grid-cols-3">
                <Input
                  label="Email"
                  placeholder="user@company.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                />
                <Input
                  label="Name"
                  placeholder="John Doe"
                  value={inviteName}
                  onChange={(e) => setInviteName(e.target.value)}
                />
                <div className="space-y-1.5">
                  <label className="block text-sm font-medium text-text-2">Role</label>
                  <select
                    value={inviteRole}
                    onChange={(e) => setInviteRole(e.target.value)}
                    className="w-full rounded-lg border border-border bg-background px-3 py-2 text-sm text-text"
                  >
                    <option value="user">User</option>
                    <option value="tenant_admin">Admin</option>
                  </select>
                </div>
              </div>
              <div className="mt-3 flex gap-2">
                <Button size="sm" loading={inviting} onClick={handleInvite}>
                  Send Invite
                </Button>
                <Button size="sm" variant="ghost" onClick={() => setShowInvite(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          )}

          {/* Users List */}
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border text-left text-text-3">
                  <th className="py-3 pr-4 font-medium">User</th>
                  <th className="py-3 pr-4 font-medium">Role</th>
                  <th className="py-3 pr-4 font-medium">Emails (30d)</th>
                  <th className="py-3 pr-4 font-medium">Joined</th>
                  <th className="py-3 font-medium"></th>
                </tr>
              </thead>
              <tbody>
                {users.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-text-4">
                      No users yet. Invite your first user above.
                    </td>
                  </tr>
                ) : (
                  users.map((u) => (
                    <tr key={u.id} className="border-b border-border last:border-0">
                      <td className="py-3 pr-4">
                        <div>
                          <p className="font-medium text-text">{u.name || u.email}</p>
                          <p className="text-xs text-text-4">{u.email}</p>
                        </div>
                      </td>
                      <td className="py-3 pr-4">
                        <Badge
                          variant={u.role === "tenant_admin" ? "navy" : "default"}
                          size="sm"
                        >
                          {u.role === "tenant_admin" ? "Admin" : "User"}
                        </Badge>
                      </td>
                      <td className="py-3 pr-4 text-text-2">{u.emails_30d}</td>
                      <td className="py-3 pr-4 text-text-4">
                        {u.created_at ? new Date(u.created_at).toLocaleDateString() : "-"}
                      </td>
                      <td className="py-3">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleRemoveUser(u.id, u.email)}
                        >
                          <Trash2 className="h-3.5 w-3.5 text-danger" />
                        </Button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </CardBody>
      </Card>

      {/* Per-User Usage Stats */}
      {stats?.user_stats && stats.user_stats.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-navy" />
              <h2 className="text-base font-semibold text-text">Usage by User</h2>
            </div>
          </CardHeader>
          <CardBody>
            <div className="space-y-2">
              {stats.user_stats.map((u) => {
                const pct = stats.emails_this_month > 0
                  ? Math.round((u.emails_month / stats.emails_this_month) * 100)
                  : 0;
                return (
                  <div key={u.id} className="flex items-center gap-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center justify-between">
                        <p className="truncate text-sm font-medium text-text">
                          {u.name || u.email}
                        </p>
                        <p className="shrink-0 text-xs text-text-3">
                          {u.emails_month} emails ({u.emails_today} today)
                        </p>
                      </div>
                      <div className="mt-1 h-1.5 w-full rounded-full bg-background-2">
                        <div
                          className="h-1.5 rounded-full bg-navy transition-all"
                          style={{ width: `${pct}%` }}
                        />
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardBody>
        </Card>
      )}

      {/* Branding Settings */}
      <Card>
        <CardHeader>
          <div className="flex items-center gap-2">
            <Palette className="h-4 w-4 text-navy" />
            <h2 className="text-base font-semibold text-text">Branding</h2>
          </div>
          <p className="text-sm text-text-3">
            Customize how your white-label product looks to your clients
          </p>
        </CardHeader>
        <CardBody className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            <Input
              label="Brand Name"
              placeholder="Your Brand"
              value={brandingName}
              onChange={(e) => setBrandingName(e.target.value)}
            />
            <Input
              label="Logo URL"
              placeholder="https://example.com/logo.png"
              value={logoUrl}
              onChange={(e) => setLogoUrl(e.target.value)}
            />
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <label className="block text-sm font-medium text-text-2">
                Primary Color
              </label>
              <div className="flex items-center gap-2">
                <input
                  type="color"
                  value={primaryColor}
                  onChange={(e) => setPrimaryColor(e.target.value)}
                  className="h-10 w-10 cursor-pointer rounded border border-border"
                />
                <Input
                  value={primaryColor}
                  onChange={(e) => setPrimaryColor(e.target.value)}
                  className="flex-1"
                />
              </div>
            </div>
          </div>

          {/* Preview */}
          <div className="rounded-lg border border-border p-4">
            <p className="mb-2 text-xs font-medium text-text-3">Preview</p>
            <div className="flex items-center gap-2">
              {logoUrl ? (
                <img src={logoUrl} alt="Preview" className="h-8 w-8 rounded-lg object-contain" />
              ) : (
                <div
                  className="flex h-8 w-8 items-center justify-center rounded-lg text-white font-bold text-sm"
                  style={{ backgroundColor: primaryColor }}
                >
                  {(brandingName || "H")[0]}
                </div>
              )}
              <span className="text-lg font-bold text-text">{brandingName || "Your Brand"}</span>
            </div>
          </div>

          <Button loading={savingBrand} onClick={handleSaveBranding}>
            Save Branding
          </Button>
        </CardBody>
      </Card>
    </div>
  );
}
