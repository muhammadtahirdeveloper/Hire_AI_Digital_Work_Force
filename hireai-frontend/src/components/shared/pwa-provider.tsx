"use client";

import { useEffect, useState } from "react";
import { WifiOff } from "lucide-react";

export function PWAProvider({ children }: { children: React.ReactNode }) {
  const [isOffline, setIsOffline] = useState(false);

  useEffect(() => {
    // Register service worker
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker
        .register("/sw.js")
        .then((reg) => {
          console.log("[PWA] Service worker registered", reg.scope);
        })
        .catch((err) => {
          console.warn("[PWA] Service worker registration failed", err);
        });
    }

    // Online/offline detection
    const handleOnline = () => setIsOffline(false);
    const handleOffline = () => setIsOffline(true);

    setIsOffline(!navigator.onLine);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, []);

  return (
    <>
      {isOffline && (
        <div className="fixed top-0 left-0 right-0 z-[100] flex items-center justify-center gap-2 bg-warning px-4 py-2 text-center text-sm font-medium text-white">
          <WifiOff className="h-4 w-4" />
          You&apos;re offline — some features may be unavailable
        </div>
      )}
      {children}
    </>
  );
}
