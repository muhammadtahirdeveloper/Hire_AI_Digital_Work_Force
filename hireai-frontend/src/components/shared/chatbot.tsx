"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import { Bot, X, Send, MessageCircle, Mail, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

// --- Types ---

interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

// --- System prompts ---

const DASHBOARD_SYSTEM_PROMPT = `You are HireAI's intelligent customer support agent.
HireAI is an AI-powered email management platform that uses Claude AI agents
to automatically process, classify, and respond to Gmail emails.

Platform details:
- 4 agents: General, HR, Real Estate, E-commerce
- 3 plans: Starter ($19, Haiku 3.5), Professional ($49, Sonnet 4.5), Enterprise ($99, Sonnet 4.5)
- Free trial: 7 days, Sonnet 4.5
- Contact: hireaidigitalemployee@gmail.com

Common issues you can help with:
1. Gmail not connecting → Ask to check OAuth, suggest reconnect
2. Agent not processing → Check if paused, check Gmail token
3. Wrong emails being handled → Suggest checking agent config
4. Trial expiry → Explain plans, encourage upgrade
5. Billing questions → Direct to billing page or email

Be friendly, concise, and helpful. Always offer to escalate to human support
(hireaidigitalemployee@gmail.com) for complex issues.
Keep responses under 100 words unless detailed explanation needed.`;

const LANDING_SYSTEM_PROMPT = `You are HireAI's friendly sales and information assistant.
HireAI is an AI-powered email management platform that uses Claude AI agents
to automatically process, classify, and respond to Gmail emails.

Key information:
- 4 agent types: General, HR, Real Estate, E-commerce
- 3 plans: Starter ($19/mo), Professional ($49/mo), Enterprise ($99/mo)
- Free 7-day trial with full features
- Processes Gmail emails automatically using Claude AI
- Contact: hireaidigitalemployee@gmail.com

Focus on:
- Explaining features and benefits
- Helping users pick the right plan
- Answering security/privacy questions
- Encouraging signups for the free trial

Be enthusiastic but concise. Keep responses under 100 words.`;

const dashboardSuggestions = [
  "How do I connect Gmail?",
  "My agent isn't working",
  "How do I change my plan?",
  "What does the HR agent do?",
];

const landingSuggestions = [
  "What is HireAI?",
  "How does the free trial work?",
  "Which plan is right for me?",
  "Is my Gmail data secure?",
];

// --- Typing indicator ---

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 px-3 py-2">
      <span className="h-2 w-2 animate-bounce rounded-full bg-text-4 [animation-delay:0ms]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-text-4 [animation-delay:150ms]" />
      <span className="h-2 w-2 animate-bounce rounded-full bg-text-4 [animation-delay:300ms]" />
    </div>
  );
}

// --- Component ---

export function Chatbot() {
  const { data: session } = useSession();
  const isAuthenticated = !!session?.user;

  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [exchangeCount, setExchangeCount] = useState(0);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const suggestions = isAuthenticated ? dashboardSuggestions : landingSuggestions;

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping, scrollToBottom]);

  useEffect(() => {
    if (open) inputRef.current?.focus();
  }, [open]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || isTyping) return;

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: text.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => {
      const updated = [...prev, userMsg];
      // Keep last 10 messages
      return updated.slice(-10);
    });
    setInput("");
    setIsTyping(true);

    try {
      const conversationHistory = [...messages, userMsg].slice(-10).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const res = await api.post("/api/support/chat", {
        message: text.trim(),
        conversation_history: conversationHistory,
        user_id: session?.user?.id || "anonymous",
        system_prompt: isAuthenticated ? DASHBOARD_SYSTEM_PROMPT : LANDING_SYSTEM_PROMPT,
      });

      const assistantMsg: ChatMessage = {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: res.data?.reply || "I'm sorry, I'm having trouble connecting. Please try again.",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMsg].slice(-10));
      setExchangeCount((c) => c + 1);
    } catch {
      // Fallback response when API is unavailable
      const fallback: ChatMessage = {
        id: `a-${Date.now()}`,
        role: "assistant",
        content: isAuthenticated
          ? "I'm currently unable to connect to the support service. For immediate help, please email us at hireaidigitalemployee@gmail.com or check the Settings page for common solutions."
          : "I'm currently unable to connect. For questions about HireAI, please email hireaidigitalemployee@gmail.com or start your free trial to explore the platform.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, fallback].slice(-10));
      setExchangeCount((c) => c + 1);
    }

    setIsTyping(false);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendMessage(input);
  };

  const formatTime = (date: Date) =>
    date.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });

  const showEscalation = exchangeCount >= 3;

  return (
    <>
      {/* Collapsed button */}
      {!open && (
        <button
          onClick={() => setOpen(true)}
          className="fixed bottom-6 right-6 z-50 flex items-center gap-2 rounded-full bg-navy px-5 py-3 text-sm font-medium text-white shadow-lg transition-all hover:bg-navy-dark hover:shadow-xl"
        >
          <MessageCircle className="h-5 w-5" />
          Need help?
        </button>
      )}

      {/* Expanded chat window */}
      {open && (
        <div className="fixed bottom-6 right-6 z-50 flex h-[500px] w-[380px] flex-col overflow-hidden rounded-2xl border border-border bg-background shadow-2xl">
          {/* Header */}
          <div className="flex items-center justify-between border-b border-border bg-navy px-4 py-3">
            <div className="flex items-center gap-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-white/20">
                <Bot className="h-5 w-5 text-white" />
              </div>
              <div>
                <p className="text-sm font-semibold text-white">HireAI Assistant</p>
                <div className="flex items-center gap-1.5">
                  <span className="relative flex h-2 w-2">
                    <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-green-400 opacity-75" />
                    <span className="relative inline-flex h-2 w-2 rounded-full bg-green-400" />
                  </span>
                  <span className="text-[10px] text-white/70">
                    Powered by Claude
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="rounded-lg p-1.5 text-white/70 transition-colors hover:bg-white/10 hover:text-white"
              aria-label="Minimize chat"
            >
              <X className="h-4 w-4" />
            </button>
          </div>

          {/* Messages area */}
          <div className="flex-1 overflow-y-auto px-4 py-4">
            {/* Welcome message */}
            {messages.length === 0 && (
              <div className="space-y-4">
                <div className="flex gap-2">
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-navy/10">
                    <Bot className="h-4 w-4 text-navy" />
                  </div>
                  <div className="rounded-xl rounded-tl-none bg-background-1 px-3 py-2 text-sm text-text-2">
                    {isAuthenticated
                      ? "Hi there! I'm your HireAI assistant. How can I help you today?"
                      : "Welcome! I'm the HireAI assistant. Ask me anything about our AI email agents."}
                  </div>
                </div>

                {/* Quick suggestions */}
                <div className="flex flex-wrap gap-2 pl-9">
                  {suggestions.map((s) => (
                    <button
                      key={s}
                      onClick={() => sendMessage(s)}
                      className="rounded-full border border-border px-3 py-1.5 text-xs text-text-2 transition-colors hover:border-navy hover:bg-navy/5 hover:text-navy"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Chat messages */}
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={cn(
                  "mb-3 flex gap-2",
                  msg.role === "user" ? "flex-row-reverse" : "flex-row"
                )}
              >
                {msg.role === "assistant" && (
                  <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-navy/10">
                    <Bot className="h-4 w-4 text-navy" />
                  </div>
                )}
                <div
                  className={cn(
                    "max-w-[75%] rounded-xl px-3 py-2 text-sm",
                    msg.role === "user"
                      ? "rounded-tr-none bg-navy text-white"
                      : "rounded-tl-none bg-background-1 text-text-2"
                  )}
                >
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  <p
                    className={cn(
                      "mt-1 text-[10px]",
                      msg.role === "user" ? "text-white/50" : "text-text-4"
                    )}
                  >
                    {formatTime(msg.timestamp)}
                  </p>
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {isTyping && (
              <div className="mb-3 flex gap-2">
                <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-navy/10">
                  <Bot className="h-4 w-4 text-navy" />
                </div>
                <div className="rounded-xl rounded-tl-none bg-background-1">
                  <TypingIndicator />
                </div>
              </div>
            )}

            {/* Escalation */}
            {showEscalation && !isTyping && messages.length > 0 && (
              <div className="mb-3 rounded-lg border border-border bg-background-1 p-3">
                <p className="text-xs text-text-3">
                  For complex issues, our team responds within 24 hours.
                </p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <a
                    href="mailto:hireaidigitalemployee@gmail.com"
                    className="inline-flex items-center gap-1.5 rounded-md bg-navy px-3 py-1.5 text-xs font-medium text-white transition-colors hover:bg-navy-dark"
                  >
                    <Mail className="h-3 w-3" />
                    Email Support Team
                  </a>
                  <a
                    href="/reviews"
                    className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-1.5 text-xs font-medium text-text-2 transition-colors hover:bg-background-2"
                  >
                    <BookOpen className="h-3 w-3" />
                    View Documentation
                  </a>
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>

          {/* Input area */}
          <form
            onSubmit={handleSubmit}
            className="flex items-center gap-2 border-t border-border px-4 py-3"
          >
            <input
              ref={inputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask anything..."
              disabled={isTyping}
              className="flex-1 rounded-lg border border-border bg-background px-3 py-2 text-sm text-text placeholder:text-text-4 focus:outline-none focus:ring-2 focus:ring-navy disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={!input.trim() || isTyping}
              className="flex h-9 w-9 items-center justify-center rounded-lg bg-navy text-white transition-colors hover:bg-navy-dark disabled:opacity-50"
              aria-label="Send message"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}
