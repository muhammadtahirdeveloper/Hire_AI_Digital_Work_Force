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

// Module-level cache to prevent duplicate /auth/user/ fetches across
// multiple component instances that call useAuth().
let _metaCache: { email: string; data: UserMeta; ts: number } | null = null;
const META_CACHE_TTL = 30_000; // 30 seconds

export function useAuth() {
  const [state, setState] = useState<AuthState>({ user: null, loading: true });
  const supabase = createClient();

  const fetchUserMeta = useCallback(async (supabaseUser: User) => {
    const email = supabaseUser.email || "";
    if (!email) return;

    // Return cached result if fresh
    if (_metaCache && _metaCache.email === email && Date.now() - _metaCache.ts < META_CACHE_TTL) {
      setState((prev) => prev.user ? { ...prev, user: { ...prev.user, meta: _metaCache!.data } } : prev);
      return;
    }

    try {
      const res = await fetch(`${API_URL}/auth/user/${encodeURIComponent(email)}`);
      if (res.ok) {
        const data = await res.json();
        const meta: UserMeta = {
          id: data.id || supabaseUser.id,
          email: data.email || email,
          name: data.name || supabaseUser.user_metadata?.full_name || "",
          image: data.image || supabaseUser.user_metadata?.avatar_url || "",
          tier: data.tier || "trial",
          agentType: data.agent_type || "general",
          isActive: data.is_active ?? true,
          setupComplete: data.setup_complete ?? false,
          trialEndDate: data.trial_end_date,
        };
        _metaCache = { email, data: meta, ts: Date.now() };
        setState((prev) => prev.user ? { ...prev, user: { ...prev.user, meta } } : prev);
      }
    } catch {
      // Non-fatal
    }
  }, []);

  const syncBackendToken = useCallback(async (supabaseUser: User) => {
    // If we already have a backend token, just fetch user meta
    const existingToken = getAuthToken();
    if (existingToken) {
      await fetchUserMeta(supabaseUser);
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
          await fetchUserMeta(supabaseUser);
        }
      }
    } catch {
      // Non-fatal
    }
  }, [supabase, fetchUserMeta]);

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
