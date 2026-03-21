"use client";

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";

// --- Types ---

export type Locale = "en" | "ur" | "ar" | "hi";

export interface LocaleInfo {
  code: Locale;
  name: string;
  nativeName: string;
  dir: "ltr" | "rtl";
}

export const LOCALES: LocaleInfo[] = [
  { code: "en", name: "English", nativeName: "EN", dir: "ltr" },
  { code: "ur", name: "Urdu", nativeName: "\u0627\u0631\u062F\u0648", dir: "rtl" },
  { code: "ar", name: "Arabic", nativeName: "\u0639\u0631\u0628\u064A", dir: "rtl" },
  { code: "hi", name: "Hindi", nativeName: "\u0939\u093F\u0902\u0926\u0940", dir: "ltr" },
];

type Messages = Record<string, Record<string, string>>;

interface I18nContextValue {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string) => string;
  dir: "ltr" | "rtl";
  isRTL: boolean;
  localeInfo: LocaleInfo;
}

const I18nContext = createContext<I18nContextValue | null>(null);

// --- Message cache ---

const messageCache: Partial<Record<Locale, Messages>> = {};

async function loadMessages(locale: Locale): Promise<Messages> {
  if (messageCache[locale]) return messageCache[locale]!;
  try {
    const mod = await import(`../../messages/${locale}.json`);
    const data = mod.default || mod;
    messageCache[locale] = data;
    return data;
  } catch {
    // Fallback to English
    if (locale !== "en") return loadMessages("en");
    return {};
  }
}

// --- Provider ---

const STORAGE_KEY = "hireai-locale";

function getStoredLocale(): Locale {
  if (typeof window === "undefined") return "en";
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored && ["en", "ur", "ar", "hi"].includes(stored)) return stored as Locale;
  return "en";
}

export function LocaleProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>("en");
  const [messages, setMessages] = useState<Messages>({});
  const [ready, setReady] = useState(false);

  // Load stored locale on mount
  useEffect(() => {
    const stored = getStoredLocale();
    setLocaleState(stored);
  }, []);

  // Load messages when locale changes
  useEffect(() => {
    let cancelled = false;
    loadMessages(locale).then((msgs) => {
      if (!cancelled) {
        setMessages(msgs);
        setReady(true);
      }
    });
    return () => { cancelled = true; };
  }, [locale]);

  // Update HTML dir and lang attributes
  useEffect(() => {
    const info = LOCALES.find((l) => l.code === locale) || LOCALES[0];
    document.documentElement.setAttribute("dir", info.dir);
    document.documentElement.setAttribute("lang", locale);
  }, [locale]);

  const setLocale = useCallback((newLocale: Locale) => {
    setLocaleState(newLocale);
    localStorage.setItem(STORAGE_KEY, newLocale);
  }, []);

  const t = useCallback(
    (key: string): string => {
      // key format: "section.key" e.g. "nav.overview"
      const parts = key.split(".");
      if (parts.length !== 2) return key;
      const [section, field] = parts;
      const value = messages[section]?.[field];
      return value || key;
    },
    [messages]
  );

  const localeInfo = LOCALES.find((l) => l.code === locale) || LOCALES[0];

  const value: I18nContextValue = {
    locale,
    setLocale,
    t,
    dir: localeInfo.dir,
    isRTL: localeInfo.dir === "rtl",
    localeInfo,
  };

  // Render children immediately with fallback keys until messages load
  if (!ready && locale !== "en") {
    return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
  }

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

// --- Hook ---

export function useLocale() {
  const ctx = useContext(I18nContext);
  if (!ctx) {
    // Fallback for components outside provider
    return {
      locale: "en" as Locale,
      setLocale: () => {},
      t: (key: string) => key,
      dir: "ltr" as const,
      isRTL: false,
      localeInfo: LOCALES[0],
    };
  }
  return ctx;
}

// --- Date formatting ---

const LOCALE_MAP: Record<Locale, string> = {
  en: "en-US",
  ur: "ur-PK",
  ar: "ar-SA",
  hi: "hi-IN",
};

export function formatLocalizedDate(
  date: string | Date,
  locale: Locale,
  options?: Intl.DateTimeFormatOptions
): string {
  const d = typeof date === "string" ? new Date(date) : date;
  const intlLocale = LOCALE_MAP[locale] || "en-US";
  const defaultOpts: Intl.DateTimeFormatOptions = {
    year: "numeric",
    month: "short",
    day: "numeric",
    ...options,
  };
  try {
    return new Intl.DateTimeFormat(intlLocale, defaultOpts).format(d);
  } catch {
    return d.toLocaleDateString();
  }
}

export function formatLocalizedDateTime(
  date: string | Date,
  locale: Locale
): string {
  return formatLocalizedDate(date, locale, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function formatLocalizedRelativeTime(
  date: string | Date,
  locale: Locale
): string {
  const d = typeof date === "string" ? new Date(date) : date;
  const now = Date.now();
  const diff = now - d.getTime();
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  const intlLocale = LOCALE_MAP[locale] || "en-US";

  try {
    const rtf = new Intl.RelativeTimeFormat(intlLocale, { numeric: "auto" });
    if (seconds < 60) return rtf.format(-seconds, "second");
    if (minutes < 60) return rtf.format(-minutes, "minute");
    if (hours < 24) return rtf.format(-hours, "hour");
    if (days < 30) return rtf.format(-days, "day");
    return formatLocalizedDate(d, locale);
  } catch {
    // Fallback
    if (minutes < 1) return "just now";
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  }
}
