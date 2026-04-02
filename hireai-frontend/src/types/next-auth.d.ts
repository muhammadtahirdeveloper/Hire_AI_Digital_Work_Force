// Legacy type definitions preserved for compatibility.
// Auth is now handled by Supabase + useAuth() hook.

export interface HireAIUser {
  id: string;
  email: string;
  name: string;
  image?: string;
  tier: string;
  agentType: string;
  isActive: boolean;
  setupComplete: boolean;
  trialEndDate?: string;
}

export interface HireAISession {
  user: HireAIUser;
  accessToken?: string;
}
