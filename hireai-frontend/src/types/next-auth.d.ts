import "next-auth";

declare module "next-auth" {
  interface Session {
    user: {
      id: string;
      email: string;
      name: string;
      image?: string;
      tier: string;
      agentType: string;
      isActive: boolean;
      setupComplete: boolean;
      trialEndDate?: string;
    };
  }

  interface User {
    id: string;
    email: string;
    name: string;
    image?: string;
    tier?: string;
    agentType?: string;
    isActive?: boolean;
    setupComplete?: boolean;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    id?: string;
    tier?: string;
    agentType?: string;
    isActive?: boolean;
    setupComplete?: boolean;
    trialEndDate?: string;
    accessToken?: string;
  }
}
