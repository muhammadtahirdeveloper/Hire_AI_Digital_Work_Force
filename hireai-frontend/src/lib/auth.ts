import type { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import CredentialsProvider from "next-auth/providers/credentials";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID || "",
      clientSecret: process.env.GOOGLE_CLIENT_SECRET || "",
    }),
    CredentialsProvider({
      name: "credentials",
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" },
      },
      async authorize(credentials) {
        if (!credentials?.email || !credentials?.password) return null;

        try {
          const res = await fetch(`${API_URL}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: credentials.email,
              password: credentials.password,
            }),
          });
          const json = await res.json();
          const data = json?.data || json;
          if (data?.user) return data.user;
          return null;
        } catch {
          return null;
        }
      },
    }),
  ],
  session: {
    strategy: "jwt",
    maxAge: 30 * 24 * 60 * 60, // 30 days
  },
  pages: {
    signIn: "/login",
    newUser: "/signup",
  },
  callbacks: {
    async signIn({ user, account }) {
      if (account?.provider === "google") {
        try {
          await fetch(`${API_URL}/auth/google-login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              email: user.email,
              name: user.name,
              image: user.image,
              google_id: account.providerAccountId,
            }),
          });
        } catch {
          // User will be created on first login
        }
      }
      return true;
    },
    async jwt({ token, user, account }) {
      if (user) {
        token.id = user.id;
        token.email = user.email;
        token.name = user.name;
        token.image = user.image;
        token.setupComplete = false;
      }

      if (account?.provider === "google") {
        token.accessToken = account.access_token;
      }

      // Always fetch fresh setup_complete from backend using native fetch
      // (axios api instance is unreliable in server-side NextAuth callbacks)
      if (token.email) {
        try {
          const res = await fetch(`${API_URL}/auth/user/${token.email}`);
          if (res.ok) {
            const data = await res.json();
            token.setupComplete = data?.setup_complete === true;
            token.tier = data?.tier || "trial";
            token.agentType = data?.agent_type || "general";
            token.isActive = data?.is_active ?? true;
            token.trialEndDate = data?.trial_end_date;
          }
        } catch {
          // If fetch fails, keep existing token values
          token.setupComplete = token.setupComplete || false;
          token.tier = token.tier || "trial";
          token.agentType = token.agentType || "general";
          token.isActive = token.isActive ?? true;
        }
      }

      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = (token.id || token.sub) as string;
        session.user.setupComplete = (token.setupComplete as boolean) ?? false;
        session.user.tier = (token.tier as string) || "trial";
        session.user.agentType = (token.agentType as string) || "general";
        session.user.isActive = (token.isActive as boolean) ?? true;
        session.user.trialEndDate = token.trialEndDate as string | undefined;
      }
      return session;
    },
  },
};
