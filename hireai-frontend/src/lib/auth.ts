import type { NextAuthOptions } from "next-auth";
import GoogleProvider from "next-auth/providers/google";
import CredentialsProvider from "next-auth/providers/credentials";
import { api } from "./api";

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
          const res = await api.post("/auth/login", {
            email: credentials.email,
            password: credentials.password,
          });
          const data = res.data?.data || res.data;
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
          await api.post("/auth/google-login", {
            email: user.email,
            name: user.name,
            image: user.image,
            google_id: account.providerAccountId,
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
      }

      if (account?.provider === "google") {
        token.accessToken = account.access_token;
      }

      // Fetch user profile from backend on each token refresh
      if (token.email) {
        try {
          const res = await api.get(`/auth/user/${token.email}`);
          if (res.data) {
            token.tier = res.data.tier || "trial";
            token.agentType = res.data.agent_type || "general";
            token.isActive = res.data.is_active ?? true;
            token.setupComplete = res.data.setup_complete ?? false;
            token.trialEndDate = res.data.trial_end_date;
          }
        } catch {
          // Defaults for new users
          token.tier = token.tier || "trial";
          token.agentType = token.agentType || "general";
          token.isActive = token.isActive ?? true;
          token.setupComplete = token.setupComplete ?? false;
        }
      }

      return token;
    },
    async session({ session, token }) {
      if (session.user) {
        session.user.id = token.id as string;
        session.user.tier = (token.tier as string) || "trial";
        session.user.agentType = (token.agentType as string) || "general";
        session.user.isActive = (token.isActive as boolean) ?? true;
        session.user.setupComplete = (token.setupComplete as boolean) ?? false;
        session.user.trialEndDate = token.trialEndDate as string | undefined;
      }
      return session;
    },
  },
};
