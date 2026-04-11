/**
 * User types
 */
export interface User {
  id: string;
  email: string;
  name: string;
  image?: string;
  tier: "trial" | "tier1" | "tier2" | "tier3";
  agentType: "general" | "hr" | "real_estate" | "ecommerce";
  isActive: boolean;
  trialStartDate?: Date;
  trialEndDate?: Date;
  setupComplete: boolean;
}

/**
 * Agent types
 */
export type AgentType = "general" | "hr" | "real_estate" | "ecommerce";

export interface Agent {
  name: string;
  type: AgentType;
  description: string;
  icon: string;
  features: string[];
}

/**
 * Email types
 */
export interface Email {
  id: string;
  from: string;
  subject: string;
  body: string;
  category: string;
  action: "auto_replied" | "draft_created" | "escalated" | "blocked";
  timestamp: Date;
  read: boolean;
}

/**
 * Dashboard stats
 */
export interface DashboardStats {
  emails_today: number;
  auto_replied_today: number;
  escalated_today: number;
  avg_response_time: number;
  emails_yesterday: number;
  auto_replied_yesterday: number;
  agent_uptime_hours: number;
  emails_in_queue: number;
  emails_this_month?: number;
}

/**
 * Agent status
 */
export interface AgentStatus {
  is_running: boolean;
  is_paused: boolean;
  test_mode: boolean;
  agent_type: AgentType;
  tier: string;
  model: string;
  gmail_connected: string;
  gmail_valid: boolean;
  last_processed?: Date;
  last_error?: string;
  trial_end_date?: string;
  trial_days_left?: number;
  setup_complete?: boolean;
}

/**
 * Plan/Tier types
 */
export type Tier = "tier1" | "tier2" | "tier3";

export interface Plan {
  id: Tier;
  name: string;
  price: number;
  model: string;
  features: string[];
  maxEmails: number;
  maxAccounts: number;
}
