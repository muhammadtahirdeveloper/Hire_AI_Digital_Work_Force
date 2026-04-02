"use client";

import { useEffect, useState, useCallback } from "react";
import { createClient } from "@/lib/supabase/client";
import { setAuthToken, getAuthToken, removeAuthToken } from "@/lib/api";
import type { User } from "@supabase/supabase-js";

interface UserMeta {
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

interface AuthState {
  user: (User & { meta?: UserMeta }) | null;
  loading: boolean;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function useAuth() {
  const [state, setState] = useState<AuthState>({ user: null, loading: true });
  const supabase = createClient();

  const syncBackendToken = useCallback(async (supabaseUser: User) => {
    // If we already have a backend token, just fetch user meta
    const existingToken = getAuthToken();
    if (existingToken) {
      await fetchUserMeta(supabaseUser, existingToken);
      return;
    }

    // Get Supabase access token and sync to backend
    const { data: { session } } = await supabase.auth.getSession();
    if (!session?.access_token) return;

    try {
      const res = await fetch(`${API_URL}/auth/supabase-sync`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: supabaseUser.email,
          name: supabaseUser.user_metadata?.full_name || supabaseUser.user_metadata?.name || supabaseUser.email?.split("@")[0] || "",
          image: supabaseUser.user_metadata?.avatar_url || "",
          supabase_id: supabaseUser.id,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        const token = data?.data?.token || data?.data?.access_token || data?.token || "";
        if (token) {
          setAuthToken(token);
          await fetchUserMeta(supabaseUser, token);
        }
      }
    } catch {
      // Non-fatal
    }
  }, [supabase]);

  // eslint-disable-next-line @typescript-eslint/no-unused-vars
  const fetchUserMeta = async (supabaseUser: User, _token?: string) => {
    try {
      const res = await fetch(`${API_URL}/auth/user/${encodeURIComponent(supabaseUser.email || "")}`);
      if (res.ok) {
        const data = await res.json();
        setState((prev) => ({
          ...prev,
          user: prev.user
            ? { ...prev.user, meta: {
                id: data.id || supabaseUser.id,
                email: data.email || supabaseUser.email || "",
                name: data.name || supabaseUser.user_metadata?.full_name || "",
                image: data.image || supabaseUser.user_metadata?.avatar_url || "",
                tier: data.tier || "trial",
                agentType: data.agent_type || "general",
                isActive: data.is_active ?? true,
                setupComplete: data.setup_complete ?? false,
                trialEndDate: data.trial_end_date,
              }}
            : prev.user,
        }));
      }
    } catch {
      // Non-fatal
    }
  };

  useEffect(() => {
    const getUser = async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        setState({ user, loading: false });
        await syncBackendToken(user);
      } else {
        setState({ user: null, loading: false });
      }
    };

    getUser();

    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (_event, session) => {
        if (session?.user) {
          setState({ user: session.user, loading: false });
          await syncBackendToken(session.user);
        } else {
          removeAuthToken();
          setState({ user: null, loading: false });
        }
      }
    );

    return () => subscription.unsubscribe();
  }, [supabase, syncBackendToken]);

  const signOut = async () => {
    removeAuthToken();
    await supabase.auth.signOut();
    setState({ user: null, loading: false });
  };

  return {
    user: state.user,
    loading: state.loading,
    signOut,
    supabase,
    // Convenience accessors matching old useSession pattern
    session: state.user
      ? {
          user: {
            id: state.user.meta?.id || state.user.id,
            email: state.user.email || "",
            name: state.user.meta?.name || state.user.user_metadata?.full_name || "",
            image: state.user.meta?.image || state.user.user_metadata?.avatar_url || "",
            tier: state.user.meta?.tier || "trial",
            agentType: state.user.meta?.agentType || "general",
            isActive: state.user.meta?.isActive ?? true,
            setupComplete: state.user.meta?.setupComplete ?? false,
            trialEndDate: state.user.meta?.trialEndDate,
          },
        }
      : null,
    status: state.loading ? "loading" as const : state.user ? "authenticated" as const : "unauthenticated" as const,
  };
}
