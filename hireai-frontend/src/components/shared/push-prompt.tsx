"use client";

import { useEffect, useState } from "react";
import { Bell, X } from "lucide-react";
import { api } from "@/lib/api";

export function PushPrompt() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    // Only show if push is supported and not already granted/denied
    if (!("Notification" in window) || !("serviceWorker" in navigator)) return;
    if (Notification.permission !== "default") return;

    // Don't show if user has dismissed before (stored in localStorage)
    if (localStorage.getItem("hireai-push-dismissed")) return;

    // Wait a bit before showing
    const timer = setTimeout(() => setShow(true), 5000);
    return () => clearTimeout(timer);
  }, []);

  const handleEnable = async () => {
    try {
      const permission = await Notification.requestPermission();
      if (permission === "granted") {
        const reg = await navigator.serviceWorker.ready;
        const subscription = await reg.pushManager.subscribe({
          userVisibleOnly: true,
          applicationServerKey: process.env.NEXT_PUBLIC_VAPID_PUBLIC_KEY,
        });

        // Send subscription to backend
        await api.post("/api/notifications/subscribe", {
          endpoint: subscription.endpoint,
          keys: {
            p256dh: btoa(
              String.fromCharCode(...new Uint8Array(subscription.getKey("p256dh")!))
            ),
            auth: btoa(
              String.fromCharCode(...new Uint8Array(subscription.getKey("auth")!))
            ),
          },
        });
      }
    } catch (err) {
      console.warn("[push] Subscription failed:", err);
    }
    setShow(false);
  };

  const handleDismiss = () => {
    localStorage.setItem("hireai-push-dismissed", "1");
    setShow(false);
  };

  if (!show) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 w-80 rounded-xl border border-border bg-background p-4 shadow-lg">
      <button
        onClick={handleDismiss}
        className="absolute right-2 top-2 text-text-4 hover:text-text"
      >
        <X className="h-4 w-4" />
      </button>
      <div className="flex items-start gap-3">
        <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-navy-light">
          <Bell className="h-5 w-5 text-navy" />
        </div>
        <div>
          <h4 className="text-sm font-semibold text-text">Enable Notifications</h4>
          <p className="mt-1 text-xs text-text-3">
            Get notified when urgent emails need your attention or new leads arrive.
          </p>
          <div className="mt-3 flex gap-2">
            <button
              onClick={handleEnable}
              className="rounded-lg bg-navy px-3 py-1.5 text-xs font-medium text-white hover:bg-navy-hover transition-colors"
            >
              Enable
            </button>
            <button
              onClick={handleDismiss}
              className="rounded-lg px-3 py-1.5 text-xs font-medium text-text-3 hover:bg-background-2 transition-colors"
            >
              Not Now
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
