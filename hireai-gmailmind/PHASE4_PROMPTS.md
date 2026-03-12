# PHASE 4 PROMPTS — HireAI Platform
## Next.js Frontend + Dashboard + All Features
### Complete Implementation Guide for Claude Code

---

## CONTEXT (Read Before Starting)

**Project:** HireAI — Intelligent Email Agents Platform  
**Backend:** FastAPI already built (Phases 1–3) running at port 8000  
**Database:** Neon PostgreSQL (cloud)  
**AI Models:**
- Free Trial → `claude-sonnet-4-5`
- Tier 1 → `claude-haiku-3-5`
- Tier 2 → `claude-sonnet-4-5`
- Tier 3 → `claude-sonnet-4-5`

**Contact:** hireaidigitalemployee@gmail.com  
**Platform Name:** HireAI  
**Design:** Dark Gray (#0A0A0A) + Light White (#FFFFFF) — user can toggle  
**Font:** Geist (Vercel's font)  
**Accent:** Navy Blue (#1D4ED8)  

**Pricing:**
- Tier 1 Starter: $19/month → claude-haiku-3-5
- Tier 2 Professional: $49/month → claude-sonnet-4-5
- Tier 3 Enterprise: $99/month → claude-sonnet-4-5
- Free Trial: 7 days → claude-sonnet-4-5 (no credit card)

---

## PROMPT 36 — Next.js Project Setup

```
Please set up a new Next.js 14 project for HireAI platform.

Project location: /mnt/e/Digital_AI_WorkForce/hireai-frontend/

Requirements:

1. Create Next.js 14 app with App Router:
   npx create-next-app@latest hireai-frontend --typescript --tailwind --app --src-dir --import-alias "@/*"

2. Install all required packages:
   npm install next-auth @next-auth/prisma-adapter
   npm install @prisma/client prisma
   npm install axios swr
   npm install lucide-react
   npm install clsx tailwind-merge
   npm install @radix-ui/react-dialog @radix-ui/react-dropdown-menu @radix-ui/react-switch @radix-ui/react-tabs @radix-ui/react-tooltip @radix-ui/react-avatar @radix-ui/react-select
   npm install next-themes
   npm install recharts
   npm install react-hot-toast
   npm install framer-motion
   npm install @tanstack/react-query

3. Setup folder structure:
   src/
   ├── app/
   │   ├── (marketing)/          ← Public pages (landing, pricing)
   │   │   ├── page.tsx          ← Landing page
   │   │   ├── pricing/page.tsx
   │   │   ├── features/page.tsx
   │   │   └── layout.tsx
   │   ├── (auth)/               ← Auth pages
   │   │   ├── login/page.tsx
   │   │   ├── signup/page.tsx
   │   │   └── layout.tsx
   │   ├── dashboard/            ← Protected dashboard
   │   │   ├── page.tsx          ← Overview
   │   │   ├── agent/page.tsx
   │   │   ├── emails/page.tsx
   │   │   ├── analytics/page.tsx
   │   │   ├── settings/page.tsx
   │   │   ├── billing/page.tsx
   │   │   ├── gmail/page.tsx
   │   │   └── layout.tsx
   │   ├── api/
   │   │   ├── auth/[...nextauth]/route.ts
   │   │   └── webhook/route.ts
   │   ├── layout.tsx
   │   └── globals.css
   ├── components/
   │   ├── ui/                   ← Reusable UI components
   │   ├── marketing/            ← Landing page components
   │   ├── dashboard/            ← Dashboard components
   │   └── shared/               ← Shared components
   ├── lib/
   │   ├── auth.ts
   │   ├── api.ts
   │   └── utils.ts
   ├── hooks/
   ├── types/
   └── store/

4. Configure tailwind.config.ts with HireAI design system:
   Colors:
   - navy: { DEFAULT: '#1D4ED8', hover: '#1E40AF', light: '#DBEAFE', soft: '#EFF6FF' }
   - background dark: '#0A0A0A'
   - surface dark: '#111111', '#161616', '#1C1C1C'
   - border dark: '#242424', '#2E2E2E'
   Font: Geist (from next/font/google)

5. Create globals.css with:
   - CSS variables for both light and dark theme
   - Light theme variables (default)
   - Dark theme variables (.dark class)
   - Base styles

6. Create lib/utils.ts with cn() helper function

7. Create .env.local template:
   NEXTAUTH_URL=http://localhost:3000
   NEXTAUTH_SECRET=generate-random-secret
   GOOGLE_CLIENT_ID=your-google-client-id
   GOOGLE_CLIENT_SECRET=your-google-client-secret
   DATABASE_URL=your-neon-db-url
   NEXT_PUBLIC_API_URL=http://localhost:8000

8. Verify project runs:
   npm run dev
   → Should open at http://localhost:3000

After completing, confirm project is running and show folder structure.
```

---

## PROMPT 37 — Design System + UI Components

```
Please build the complete HireAI design system and reusable UI components.

Design Specs:
- Platform: HireAI
- Font: Geist (already installed)
- Primary accent: Navy Blue #1D4ED8
- Supports both Light and Dark themes via next-themes
- Style: Clean, minimal — like Linear.app and Claude.ai

1. Create src/components/ui/ components:

   Button component (button.tsx):
   - Variants: primary (navy), ghost, outline, danger
   - Sizes: sm, md, lg
   - Loading state with spinner
   - Icon support left/right

   Input component (input.tsx):
   - Clean bordered style
   - Error state
   - Helper text
   - Icon prefix/suffix

   Badge component (badge.tsx):
   - Variants: default, success, warning, danger, navy, outline
   - Sizes: sm, md

   Card component (card.tsx):
   - Clean white/dark card
   - Optional hover effect
   - Header, Body, Footer sections

   Modal/Dialog component (modal.tsx):
   - Using Radix UI Dialog
   - Smooth animation
   - Dark overlay

   Switch component (switch.tsx):
   - Using Radix UI Switch
   - Navy accent when on

   Select component (select.tsx):
   - Using Radix UI Select
   - Custom styled dropdown

   Avatar component (avatar.tsx):
   - Circular with initials fallback
   - Size variants

   Skeleton component (skeleton.tsx):
   - Loading placeholder
   - Animated shimmer

   Tooltip component (tooltip.tsx):
   - Using Radix UI Tooltip

   Tabs component (tabs.tsx):
   - Using Radix UI Tabs
   - Underline style

2. Create Theme Toggle component (src/components/shared/theme-toggle.tsx):
   - Sun/Moon icon button
   - Smooth transition
   - Uses next-themes
   - Position: top-right corner always visible
   - Persists user preference in localStorage
   - Accessible keyboard navigation

3. Create Navbar component (src/components/marketing/navbar.tsx):
   - Logo: "H" mark + "HireAI" text
   - Links: Features, Pricing, Reviews, Support
   - Right: Sign in (ghost) + Start free trial (navy)
   - Theme toggle button
   - Fixed top with blur backdrop
   - Mobile hamburger menu

4. Create Dashboard Sidebar (src/components/dashboard/sidebar.tsx):
   - Logo at top
   - Navigation items with icons
   - Active state (navy background)
   - Agent status indicator (green dot + "Agent Live")
   - Collapsible on mobile
   - Theme toggle at bottom

5. Create Loading components:
   - PageLoader (full page spinner)
   - CardSkeleton
   - TableSkeleton

Verify all components work with both light and dark themes.
Show screenshots or confirm completion.
```

---

## PROMPT 38 — Landing Page (Marketing Site)

```
Please build the complete HireAI landing page at src/app/(marketing)/page.tsx

Design: Clean, minimal, professional — like Claude.ai and Linear.app
Theme: Supports both Light (default) and Dark mode
Color: Navy Blue #1D4ED8 accent on Gray/White base
Font: Geist

Build these sections in order:

1. HERO SECTION:
   - Small badge: "Now in beta · No credit card required" with navy pulsing dot
   - Main headline (large, bold, letter-spacing tight):
     "Your inbox,
      run by intelligent agents"
     ("intelligent agents" in navy gradient)
   - Subtext: "AI agents that read, classify, and respond to your emails automatically — so you stay focused on work that matters."
   - Two CTA buttons:
     → "Start 7-day free trial →" (navy, large)
     → "See how it works" (ghost, large)
   - Social proof: 4 avatar circles + "Trusted by 50+ businesses across 4 industries"
   - Subtle navy radial glow behind hero (very subtle)
   - Scroll-triggered fade-up animations (framer-motion)

2. STATS BAR:
   - Full width, border top/bottom, gray background
   - 4 stats: "50K+ Emails Processed" | "4 Specialized Agents" | "4 Industries" | "99.9% Platform Uptime"
   - Animated number counter on scroll

3. DASHBOARD PREVIEW:
   - Browser frame mockup (dots + URL bar showing app.hireai.com/dashboard)
   - Real dashboard UI inside showing:
     → Sidebar with navigation
     → Overview metrics (4 cards: Processed, Auto Replied, Escalated, Avg Response)
     → Recent Activity feed (4 email items with avatars + colored tags)
     → Agent selector (4 agent cards, HR active)
   - Subtle drop shadow
   - Scroll reveal animation

4. FEATURES SECTION:
   Title: "Everything your inbox needs to run itself"
   6 feature cards in 3x2 grid with border between them:
   - 🤖 Smart Classification
   - ✍️ Auto Reply Drafts
   - 🔐 Enterprise Security
   - ⚡ Custom Rules Engine
   - 📊 Live Analytics
   - 🔔 WhatsApp Escalation
   Each card: icon box + title + description

5. HOW IT WORKS SECTION:
   Title: "Up and running in 3 steps"
   3 horizontal steps:
   Step 1: Connect Gmail → "Link any Gmail account in 30 seconds"
   Step 2: Choose Your Agent → "Select the agent that fits your industry"
   Step 3: Go Live → "Watch your inbox run on autopilot"
   → Navy numbered circles, connected by dashed line

6. AI SUPPORT CHATBOT PREVIEW:
   Title: "Support that never sleeps"
   Chat window mockup showing:
   - Header: "HireAI Assistant · Powered by Claude · Online"
   - Message 1 (AI): "Hi! How can I help you today?"
   - Message 2 (User): "My agent stopped processing emails"
   - Message 3 (AI): "Checking status... Gmail token expired. Click here to reconnect → done in 30 seconds ✅"
   - Input bar at bottom

7. REVIEWS SECTION:
   Title: "What our users say"
   3 review cards:
   - Sarah Ahmed, HR Manager: "HireAI completely transformed how we handle recruitment emails..."
   - Mohammad Khan, Real Estate Director: "Setup took 10 minutes. By next morning, 90% of property inquiries handled..."
   - Zara Ali, E-commerce Founder: "Response time went from 6 hours to 2 minutes..."
   Each: 5 stars + review text + avatar + name + role

8. PRICING PREVIEW:
   Title: "Simple, transparent pricing"
   3 pricing cards (Starter $19, Professional $49 featured, Enterprise $99)
   Each shows: plan name, price, model name (monospace), features list, CTA button
   → "See full pricing →" link below

9. FAQ SECTION:
   Title: "Frequently asked questions"
   5 expandable questions:
   - "Is my Gmail data safe?" → "Yes. We use AES-128 encryption..."
   - "Can I use a different Gmail than my signup email?" → "Yes. You can connect any Gmail..."
   - "What happens after my free trial?" → "You choose a plan. If not, agent pauses..."
   - "Can I cancel anytime?" → "Yes. Monthly plans, cancel anytime..."
   - "What if I want custom features?" → "Contact us at hireaidigitalemployee@gmail.com..."

10. FINAL CTA BANNER:
    "Start free — see results today"
    "7 days full access. All agents. Real emails. No credit card required."
    → Navy button + email below

11. FOOTER:
    Logo | Links (Privacy, Terms, Docs, Contact) | Email: hireaidigitalemployee@gmail.com | © 2025 HireAI

All sections should:
- Have smooth scroll-reveal animations (framer-motion)
- Work perfectly in both light and dark theme
- Be fully responsive (mobile/tablet/desktop)
- Have proper SEO metadata
```

---

## PROMPT 39 — Auth Pages (Signup + Login)

```
Please build the authentication pages for HireAI.

Setup NextAuth.js with Google OAuth:

1. Configure NextAuth at src/app/api/auth/[...nextauth]/route.ts:
   - Google OAuth provider
   - Neon PostgreSQL adapter (or JWT strategy)
   - Store user: id, email, name, image, tier, trialStartDate, trialEndDate, agentType, isActive
   - On first login → auto-assign 7-day free trial
   - tier default: "trial"
   - trialEndDate: 7 days from signup

2. Build Signup page (src/app/(auth)/signup/page.tsx):
   Clean centered card design:
   - HireAI logo at top
   - Title: "Start your free trial"
   - Subtitle: "7 days free. No credit card required."
   - Large "Continue with Google" button (white with Google icon)
   - Divider: "— or —"
   - Email input + Password input + Confirm password
   - "Create account" navy button
   - Terms text: "By signing up you agree to our Terms and Privacy Policy"
   - Already have account? Sign in link
   - Theme toggle top-right

3. Build Login page (src/app/(auth)/login/page.tsx):
   Clean centered card:
   - HireAI logo
   - Title: "Welcome back"
   - "Continue with Google" button
   - Email + Password inputs
   - "Forgot password?" link
   - "Sign in" navy button
   - No account? Start free trial link
   - Theme toggle

4. Build middleware (src/middleware.ts):
   - Protect all /dashboard/* routes
   - Redirect unauthenticated users to /login
   - Redirect authenticated users from /login to /dashboard

5. Setup Wizard (src/components/dashboard/setup-wizard.tsx):
   Shown ONLY on first login (when setup_complete = false)
   Multi-step wizard:

   Step 1 — Welcome:
   "Welcome to HireAI! Let's get you set up in 3 steps."
   Progress bar at top (1/3)

   Step 2 — Connect Gmail:
   "Which Gmail should your agent monitor?"
   Input: Gmail address
   Note: "This can be different from your signup email"
   Button: "Connect Gmail →" (opens Google OAuth for Gmail scope)
   Status indicator: ✅ Connected / ⏳ Waiting

   Step 3 — Choose Agent:
   "Select an agent for your industry"
   4 agent cards (full size):
   - 🌐 General Agent — "All industries, all email types"
   - 👥 HR Agent — "CVs, interviews, candidates, job inquiries"
   - 🏠 Real Estate Agent — "Property inquiries, viewings, maintenance"
   - 🛒 E-commerce Agent — "Orders, refunds, complaints, suppliers"
   Must select one (highlighted with navy border when selected)

   Step 4 — Business Profile:
   - Business name input
   - Your name input
   - Reply tone: Formal / Friendly / Casual (radio buttons)
   - Working hours: From/To time inputs
   - WhatsApp number (optional, for alerts)

   Step 5 — Done! 🎉:
   "Your HireAI agent is live!"
   Show summary of what was configured
   "Go to Dashboard →" navy button

   Save all setup data to database via FastAPI endpoint.
   Mark setup_complete = true after Step 5.

After completing auth, verify:
- Google login works
- New user gets 7-day trial automatically
- Setup wizard shows on first login
- Protected routes redirect properly
```

---

## PROMPT 40 — Dashboard Overview Page

```
Please build the main Dashboard Overview page at src/app/dashboard/page.tsx

This is the first page users see after login. Must be stunning and functional.

Fetch all data from FastAPI backend (http://localhost:8000).
Use SWR for data fetching with auto-refresh every 30 seconds.
Show skeleton loaders while data loads.

Layout: Sidebar (already built) + Main content area

MAIN CONTENT:

1. TOP HEADER:
   - "Good morning/afternoon/evening, [User Name] 👋" (time-based greeting)
   - Subtitle: "Your agent processed X emails while you were away"
   - Right side: Status badge (● Live / ● Paused) + Trial/Plan badge
   - If trial: "Trial: X days left" warning badge in amber
   - If trial expired: Red banner "Trial expired — choose a plan to continue"

2. TRIAL BANNER (if trial active):
   Amber/yellow info bar:
   "🎉 Free Trial Active — X days remaining. Upgrade anytime to keep your agent running."
   → "Upgrade Now →" link (goes to billing page)

3. QUICK ACTIONS BAR:
   Row of action buttons:
   - ⏸️ Pause Agent / ▶️ Resume Agent (toggle)
   - 🧪 Test Mode ON/OFF toggle with label
   - 🔄 Force Sync (manually trigger email check)
   - 📊 View Full Analytics →

4. METRICS CARDS (4 cards in grid):
   - Total Processed Today: number + "↑ X% vs yesterday" in green
   - Auto Replied: number + percentage rate
   - Escalated: number + "Needs your review" link
   - Avg Response Time: "X.Xm" + "↓ X% faster" in green
   
   Each card: label + big number + trend indicator
   Hover: subtle border highlight

5. LIVE ACTIVITY FEED:
   Title: "Recent Activity" + "View all →" link
   Last 10 emails processed, each row showing:
   - Avatar circle (initials, colored by category)
   - Sender name + email subject (truncated)
   - Action taken (Auto replied / Draft created / Escalated / Blocked)
   - Category badge (CV, HR, Spam, Inquiry, etc.)
   - Time ago ("2 min ago")
   - Color coded: green=replied, blue=draft, amber=escalated, red=spam

6. AGENT STATUS CARD:
   Current agent name + tier
   Model being used (monospace): claude-sonnet-4-5
   Gmail connected: email@gmail.com ✅
   Agent uptime: X hours
   Emails in queue: X
   "Configure Agent →" button

7. QUICK STATS CHART:
   Simple bar chart (recharts)
   Last 7 days email volume
   Two bars per day: Total received vs Auto-handled
   Navy + light gray colors

8. ESCALATED EMAILS SECTION:
   Title: "⚠️ Needs Your Attention (X)"
   List of emails that were escalated:
   - Sender + subject
   - Reason for escalation
   - "Reply" button → opens Gmail
   - "Dismiss" button
   Empty state: "✅ All clear! No emails need your attention."

9. WEEKLY SUMMARY CARD:
   This week vs last week comparison:
   - Total emails: X (+Y%)
   - Time saved: ~X hours
   - Auto-reply rate: X%
   - Top category: HR / Inquiry / etc.

10. UPGRADE PROMPT (Tier 1 users only):
    Soft card at bottom:
    "🚀 Unlock unlimited emails and all 4 agents"
    "You're on the Starter plan (500 emails/month). Upgrade to Professional."
    → "Upgrade to Pro →" navy button

All data fetched from:
- GET /api/dashboard/stats
- GET /api/emails/recent?limit=10
- GET /api/agent/status
Create these FastAPI endpoints if they don't exist.

Make page fully responsive. Test both themes.
```

---

## PROMPT 41 — Agent Management Page

```
Please build the Agent Management page at src/app/dashboard/agent/page.tsx

This is where users configure their AI agent completely.

SECTIONS:

1. AGENT SELECTOR:
   Title: "Your Active Agent"
   4 large agent cards in 2x2 grid:
   
   🌐 General Agent
   - "Handles all types of emails across any industry"
   - Best for: Small businesses, freelancers
   
   👥 HR Agent  
   - "CVs, interview scheduling, candidate follow-ups, job inquiries"
   - Best for: HR teams, recruitment agencies
   
   🏠 Real Estate Agent
   - "Property inquiries, viewing requests, maintenance, lease renewals"
   - Best for: Real estate agencies, property managers
   
   🛒 E-commerce Agent
   - "Order inquiries, refunds, complaints, shipping, supplier emails"
   - Best for: Online stores, e-commerce businesses
   
   Currently active: highlighted with navy border + "Active ✓" badge
   Others: hover effect, click to switch
   
   IMPORTANT: Show warning modal when switching agent:
   "Switching agent will change how your emails are processed.
    Are you sure? Your email history will be preserved."
   → Cancel / Confirm Switch

2. TIER SELECTOR:
   Title: "Your Current Plan"
   3 tier cards side by side:
   
   Tier 1 — Starter ($19/mo) — claude-haiku-3-5
   Tier 2 — Professional ($49/mo) — claude-sonnet-4-5 ← (Most Popular badge)
   Tier 3 — Enterprise ($99/mo) — claude-sonnet-4-5
   
   Currently active: highlighted
   
   Rules:
   - Can change tier anytime BEFORE next billing date
   - After subscription renews, locked for that month
   - Show: "Next billing date: [date]. Change plan before then."
   - Show upgrade/downgrade confirmation modal

3. AI MODEL INFO:
   Show which Claude model is being used based on tier:
   Visual card with model name in monospace font
   "Your agent uses [model] for processing emails"
   Brief description of model capabilities

4. AGENT CONFIGURATION:
   Title: "Configure Your Agent"
   Form with sections:

   📧 Business Profile:
   - Business name
   - Your name (for email signatures)
   - Business type/description (used in AI prompts)
   - Reply language (English, Urdu, Arabic, etc.) — dropdown
   - Reply tone: Formal / Professional / Friendly / Casual — radio buttons

   ⏰ Working Hours:
   - Toggle: "Only process emails during working hours"
   - From time → To time
   - Working days: Mon-Fri checkboxes (Sat/Sun unchecked by default)
   - Timezone selector
   - "Outside working hours: Queue emails for next working day" option

   🎯 Email Priorities:
   - Toggle categories on/off (which email types to auto-handle)
   - Each category shows: Category name + Auto-reply toggle + Escalate toggle
   - HR: CV Applications, Interview Requests, Offer Letters, Follow-ups
   - General: Newsletters, Spam, Complaints, Leads, General
   
   🔕 Blacklist / Whitelist:
   - Blacklist: Email addresses to NEVER process (one per line textarea)
   - Whitelist (VIP): Email addresses to ALWAYS prioritize
   - Blocked keywords: Subject keywords to automatically archive

   🔔 Escalation Settings:
   - WhatsApp number for escalation alerts
   - Escalation keywords (comma-separated)
   - Escalation email (can be different from main)

   🧪 Agent Behavior:
   - Test Mode toggle: "ON = Agent only creates drafts, never sends"
   - Auto-send toggle: "OFF = All replies need your approval"
   - Max emails per day (slider: 10-500)
   - Review before send: Toggle for high-priority emails

   Save button: "Save Configuration" (navy, full width)
   Show success toast on save.

5. GMAIL CONNECTION:
   Title: "Connected Gmail Accounts"
   
   Main monitoring Gmail:
   - Email avatar + address
   - Status: ✅ Connected / ❌ Disconnected
   - Last synced: X minutes ago
   - "Reconnect" button (if disconnected)
   - "Change Gmail" button

   Reply-from Gmail (optional, Tier 2+):
   - "Agent can reply from a different Gmail"
   - Connect second Gmail button
   - Locked for Tier 1 (show upgrade prompt)

6. DANGER ZONE:
   Red bordered section at bottom:
   - "Pause Agent" — stops processing (not delete)
   - "Reset Agent" — clears all learned preferences
   - "Delete Account" — with confirmation modal

Save all changes via PATCH /api/agent/config
```

---

## PROMPT 42 — Email Log + Analytics Pages

```
Please build two pages:

=== PAGE 1: Email Log (src/app/dashboard/emails/page.tsx) ===

Shows all emails the agent has processed.

1. FILTERS BAR:
   - Search input: "Search by sender or subject..."
   - Date range picker: Today / This week / This month / Custom
   - Category filter: All / CV / Interview / Inquiry / Spam / Escalated / etc.
   - Action filter: All / Auto Replied / Draft Created / Escalated / Blocked
   - Export button: "Export CSV" (downloads filtered results)

2. EMAIL TABLE:
   Columns: Avatar | Sender | Subject | Category | Action | Time | Status
   
   Each row:
   - Colored avatar with initials
   - Sender name (bold) + email (small, gray)
   - Subject (truncated at 60 chars)
   - Category badge (colored)
   - Action badge: 
     ● Auto Replied (green)
     ● Draft Created (blue)  
     ● Escalated (amber)
     ● Blocked/Spam (red)
   - Time: "2 min ago" / "Yesterday 3:45 PM"
   - Expand row → shows full email body + agent response
   
3. EXPANDED ROW (click any email):
   Shows in expandable panel:
   - Full email body (read-only)
   - Agent's analysis: "Classified as: CV Application | Confidence: 94%"
   - Agent's response (if replied) — collapsible
   - Actions taken
   - "Open in Gmail" button

4. PAGINATION:
   20 emails per page
   Previous / Next + page numbers
   "Showing 1-20 of 537 emails"

5. EMPTY STATE:
   If no emails: "No emails processed yet. Your agent is watching your inbox."

Data from: GET /api/emails?page=1&limit=20&category=all&action=all&search=

=== PAGE 2: Analytics (src/app/dashboard/analytics/page.tsx) ===

1. DATE RANGE TABS:
   Today | This Week | This Month | Last 3 Months

2. KEY METRICS ROW (6 metric cards):
   - Total Emails Processed
   - Auto-Reply Rate (%)
   - Average Response Time
   - Emails Escalated
   - Time Saved (estimate in hours)
   - Agent Uptime (%)

3. EMAIL VOLUME CHART:
   Line chart (recharts) — emails per day
   Two lines: Total Received vs Auto-Handled
   Navy + light blue colors
   Tooltip on hover with exact numbers

4. CATEGORY BREAKDOWN:
   Donut chart — pie of email categories
   CV / Interview / Spam / General / Escalated / Other
   Legend on right with percentages

5. ACTION DISTRIBUTION:
   Horizontal bar chart:
   Auto Replied: ████████░░ 78%
   Draft Created: ███░░░░░░░ 15%
   Escalated:    ██░░░░░░░░  5%
   Blocked:      █░░░░░░░░░  2%

6. TOP SENDERS:
   Table: Rank | Sender | Emails | Auto-Handled | Category
   Top 10 most frequent email senders

7. RESPONSE TIME TREND:
   Area chart — average response time per day
   Goal line at "< 2 minutes"

8. WEEKLY COMPARISON:
   This week vs last week side-by-side mini stats
   Color coded: green if improved, red if worse

9. EXPORT REPORT:
   "Download Full Report (PDF)" button
   Generates a PDF with all analytics (use reportlab via API endpoint)

Data from: GET /api/analytics?period=week
```

---

## PROMPT 43 — Settings + Billing Pages

```
Please build two pages:

=== PAGE 1: Settings (src/app/dashboard/settings/page.tsx) ===

Organized in tabs: Profile | Notifications | Security | Database | Integrations

TAB 1 — Profile:
- Profile photo (Google avatar, can't change)
- Full name (editable)
- Display name (editable)
- Email (read-only, from Google)
- Timezone selector
- Language preference
- "Save Profile" button

TAB 2 — Notifications:
Toggle switches for each:
📧 Email Notifications:
- Weekly summary report (every Monday)
- Trial expiry reminder (2 days before)
- Agent error alerts
- Escalation email notifications

📱 WhatsApp Notifications:
- WhatsApp number input
- Test notification button: "Send Test Message"
- Escalation alerts toggle
- Daily summary toggle
- Critical error alerts toggle

🔔 In-App Notifications:
- Show browser notifications toggle
- Sound alerts toggle

TAB 3 — Security:
- Connected Google account info
- Last login: [date/time]
- Active sessions (show and revoke)
- "Sign out all devices" button (red)
- Two-factor auth info (coming soon label)
- Account creation date

TAB 4 — Custom Database (Optional Feature):
Title: "Connect Your Own Database"
Description: "For enhanced security and data control, connect your own PostgreSQL database. Your emails and agent data will be stored there instead of our shared database."

Warning box: "⚠️ Only for advanced users. If your database goes down or hits limits, your agent will pause until reconnected."

Form:
- Database URL input (masked/password type)
- Test Connection button → shows ✅ Connected or ❌ Failed
- "Activate Custom Database" button (only if test passed)

Status: 
- Using HireAI database (default) → option to switch
- Using custom database → show connection status + "Switch back" option

If using custom DB and error occurs:
- Show error banner on dashboard
- "Reconnect Database" button
- Agent auto-resumes when reconnected

TAB 5 — Integrations:
- Gmail: ✅ Connected (shows which Gmail)
- WhatsApp: ✅/❌ Connected (number shown)
- Slack: "Coming Soon" badge
- HubSpot CRM: ✅/❌ with connect button
- Calendar: "Coming Soon" badge
- Zapier: "Coming Soon" badge

=== PAGE 2: Billing (src/app/dashboard/billing/page.tsx) ===

1. CURRENT PLAN CARD:
   Shows: Plan name | Price | Status | Next billing date
   Model: claude-[model-name] in monospace
   "Change Plan" button → opens plan selector modal

2. TRIAL STATUS (if on trial):
   Big amber card:
   "🎉 Free Trial — X days remaining"
   "After trial ends, choose a plan to keep your agent running."
   Features available during trial: list
   → "Upgrade Now" navy button

3. PLAN SELECTOR MODAL:
   3 plan cards (same as landing page)
   Rules:
   - Can upgrade/downgrade anytime before billing date
   - After billing date, locked for that month
   - Show confirmation with what changes
   - "Confirm Change" button

4. PLAN CHANGE RULES (visible text):
   "📋 Plan Change Policy:
   • You can change your plan anytime before your next billing date
   • Changes take effect immediately
   • Once your subscription renews, plan is locked for that billing period
   • You can cancel anytime — agent pauses at end of period"

5. PAYMENT METHOD (Stripe — Phase 4.5):
   Placeholder section:
   "💳 Payment Method"
   "Payment integration coming soon. Contact us to arrange payment."
   Email link: hireaidigitalemployee@gmail.com
   
   (This will be replaced with Stripe in Phase 4.5)

6. BILLING HISTORY TABLE:
   Date | Plan | Amount | Status | Invoice
   (Placeholder data for now, real data in Phase 4.5)

7. CANCEL SUBSCRIPTION:
   Bottom of page, subtle:
   "Cancel subscription" text link
   → Opens confirmation modal
   "Your agent will continue until end of current period."
   → Confirm Cancel (red) / Keep Subscription (navy)

8. REFERRAL SECTION:
   "🎁 Refer a friend, get 1 month free"
   Your referral link: [copy button]
   Referrals made: 0 | Months earned: 0
   (Track referrals in database)
```

---

## PROMPT 44 — Feedback + Review System

```
Please build the complete Feedback and Review system.

1. DATABASE TABLE (add to Neon DB via migration):
   CREATE TABLE user_reviews (
     id SERIAL PRIMARY KEY,
     user_id VARCHAR NOT NULL,
     user_name VARCHAR NOT NULL,
     user_email VARCHAR NOT NULL,
     user_role VARCHAR,         -- their job title/role
     user_company VARCHAR,      -- their company name
     rating INTEGER NOT NULL,   -- 1-5 stars
     review_text TEXT,
     feature_ratings JSONB,     -- {classification: 5, speed: 4, dashboard: 5}
     is_public BOOLEAN DEFAULT false,
     is_verified BOOLEAN DEFAULT true,
     agent_type VARCHAR,        -- which agent they use
     tier VARCHAR,              -- their plan
     created_at TIMESTAMP DEFAULT NOW()
   );

2. FastAPI endpoints (add to existing API):
   POST /api/reviews          — Submit review
   GET  /api/reviews/public   — Get public reviews (for landing page)
   GET  /api/reviews/mine     — Get user's own review

3. REVIEW SUBMISSION MODAL:
   Triggers:
   - After 7 days of use (automatic popup)
   - After trial ends (prompt before choosing plan)
   - From dashboard: "⭐ Leave a Review" button in sidebar

   Modal design:
   Step 1 — Star Rating:
   Large 5-star interactive rating
   "How would you rate HireAI overall?"
   Each star animates on hover

   Step 2 — Written Review (optional):
   "Tell us about your experience (optional)"
   Textarea: min 20 chars if filled
   Placeholder: "What has HireAI helped you with most?"

   Step 3 — Feature Ratings (optional):
   Rate individual features 1-5:
   - Email Classification
   - Auto-Reply Quality  
   - Dashboard & Analytics
   - Ease of Setup
   - Customer Support

   Step 4 — Profile Info:
   - Your role/title (e.g., "HR Manager")
   - Company name (optional)
   - Make review public toggle (default: yes)

   Submit button: "Submit Review" (navy)
   Skip button: "Maybe later" (small, gray)

4. REVIEWS PAGE (public):
   /reviews route (public, no auth needed)
   
   Shows all public reviews with:
   - Overall rating: "4.9 out of 5" with big stars
   - Total reviews count
   - Rating breakdown (5★: 80%, 4★: 15%, etc.) with bars
   
   Filter by:
   - All plans / Starter / Professional / Enterprise
   - All agents / HR / Real Estate / E-commerce / General
   
   Review cards:
   - Avatar + Name + Role + Company
   - Star rating
   - Review text
   - Agent used + Plan
   - Date
   - "Verified User" badge

5. LANDING PAGE INTEGRATION:
   Reviews section on landing page:
   - Show top 3 public reviews (highest rated)
   - Fetch from GET /api/reviews/public?limit=3&sort=rating
   - "See all reviews →" link

6. DASHBOARD FEEDBACK WIDGET:
   Bottom of dashboard sidebar:
   Small "⭐ Rate HireAI" button
   Opens review modal

7. POST-TRIAL EMAIL:
   When trial ends → send email:
   Subject: "How was your HireAI trial? ⭐"
   Body: Brief summary of what agent did + review link
   (Use existing email sending in FastAPI)

Test the complete review flow end-to-end.
```

---

## PROMPT 45 — AI Support Chatbot

```
Please build the AI-powered customer support chatbot for HireAI.

This chatbot IS AN AGENT — it uses Claude API to answer questions,
diagnose problems, and help users. NOT a simple FAQ widget.

1. CHATBOT WIDGET (src/components/shared/chatbot.tsx):
   Position: Fixed bottom-right corner of ALL pages
   Collapsed state: Small navy circle with chat icon + "Need help?" text
   Expanded state: Chat window 380px wide x 500px tall
   
   Header:
   - "HireAI Assistant" + navy robot icon
   - "Powered by Claude · Always available"
   - Green dot "Online"
   - Minimize button

   Chat area:
   - AI messages: white bubble (dark mode: dark bubble), left aligned
   - User messages: navy bubble, right aligned
   - Timestamps on each message
   - Smooth scroll to latest message
   - Typing indicator (three dots animation) while AI thinks

   Input area:
   - Text input: "Ask anything..."
   - Send button (navy)
   - Enter key to send
   - Suggested quick questions (chips at start):
     → "How do I connect Gmail?"
     → "My agent isn't working"
     → "How do I change my plan?"
     → "What does the HR agent do?"

2. BACKEND ENDPOINT (add to FastAPI):
   POST /api/support/chat
   
   Request: { message: string, conversation_history: list, user_id: string }
   Response: { reply: string, suggestions: list }
   
   System prompt for support agent:
   """
   You are HireAI's intelligent customer support agent.
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
   Keep responses under 100 words unless detailed explanation needed.
   """
   
   Use claude-haiku-3-5 for chatbot (fast + cheap)

3. CONVERSATION MEMORY:
   Store last 10 messages in React state
   Send full conversation_history with each API call
   Claude maintains context throughout conversation
   
   When browser closes: conversation resets
   (No persistent storage needed for chatbot)

4. SMART DIAGNOSTICS:
   If user says "agent not working" or similar:
   → Chatbot calls: GET /api/agent/health?user_id=X
   → Gets real status: Gmail token valid? Agent running? Last processed?
   → Gives specific answer based on actual state
   
   If user says "how many emails" or similar:
   → Chatbot calls: GET /api/stats/quick?user_id=X  
   → Returns real numbers to show user

5. ESCALATION:
   If chatbot can't solve in 3 exchanges:
   Show: "For complex issues, our team responds within 24 hours."
   Button: "📧 Email Support Team" → opens mailto:hireaidigitalemployee@gmail.com
   Button: "📖 View Documentation"

6. CHATBOT ON LANDING PAGE (unauthenticated):
   Same widget but different system prompt:
   - Focuses on explaining features, pricing, trial
   - Can't access user-specific data
   - Encourage signup
   
   Pre-loaded suggestions:
   → "What is HireAI?"
   → "How does the free trial work?"
   → "Which plan is right for me?"
   → "Is my Gmail data secure?"

Verify chatbot works on both dashboard and landing page.
Test 5 different user questions and show responses.
```

---

## PROMPT 46 — Self-Healing Platform + Monitor Agent

```
Please build the self-healing platform system.

This is the background system that keeps HireAI running automatically.

1. MONITOR AGENT (add to FastAPI as background task):
   File: agents/monitor/monitor_agent.py
   
   Runs every 5 minutes via Celery scheduler.
   
   Checks for each active user:
   a) Gmail Token Health:
      - Try to list 1 email from Gmail API
      - If fails → mark token_expired = true
      - Send user notification: "Your Gmail needs reconnection"
   
   b) Agent Process Health:
      - Check last_processed_at timestamp
      - If > 30 minutes and agent should be running → restart
      - Log incident to monitor_logs table
   
   c) Database Health (for custom DB users):
      - Try simple SELECT query
      - If fails → mark db_error = true
      - Notify user: "Your custom database is unreachable. Agent paused."
      - Auto-resume when DB reconnects (checked every 5 min)
   
   d) Error Rate Check:
      - Count errors in last hour
      - If > 10 errors → pause agent, notify user + admin
   
   e) Trial Expiry Check:
      - Check trial_end_date for all trial users
      - 2 days before: send reminder email
      - On expiry: pause agent, send "Trial ended" email

2. MONITOR LOGS TABLE:
   CREATE TABLE monitor_logs (
     id SERIAL PRIMARY KEY,
     user_id VARCHAR,
     event_type VARCHAR,    -- gmail_token_expired, agent_restarted, db_error, etc.
     details JSONB,
     resolved_at TIMESTAMP,
     created_at TIMESTAMP DEFAULT NOW()
   );

3. HEALTH API ENDPOINTS:
   GET  /api/health/platform    — Overall platform health (public, no auth)
   GET  /api/health/user        — User's agent health (auth required)
   POST /api/health/restart     — Manually restart user's agent
   GET  /api/admin/health       — Admin view of all users health

4. DASHBOARD HEALTH INDICATOR:
   In dashboard header — small health indicator:
   ✅ All systems operational (green)
   ⚠️ Gmail needs reconnection (amber) + "Fix now →" link
   ❌ Agent paused — database error (red) + "Reconnect →" link
   
   Real-time check every 60 seconds via SWR

5. IMPROVEMENT AGENT (weekly task):
   File: agents/monitor/improvement_agent.py
   
   Runs every Sunday at midnight via Celery.
   
   Collects:
   - All user feedback from that week
   - Common error patterns
   - Most escalated email categories
   - Features requested in support chatbot
   
   Generates a report:
   - Markdown report: weekly_report_YYYY-MM-DD.md
   - Saves to /reports/ folder
   - Sends email to hireaidigitalemployee@gmail.com
   
   Report includes:
   - Total users: active / trial / churned
   - Total emails processed this week
   - Most common issues
   - Suggested improvements (AI generated)
   - User feedback summary

6. AUTO-HEALING SCENARIOS:
   
   Scenario A — Gmail Token Expired:
   1. Monitor detects → marks in DB
   2. Dashboard shows amber warning
   3. User clicks "Reconnect Gmail"
   4. OAuth refreshes token
   5. Agent auto-resumes within 5 min
   
   Scenario B — Custom DB Down:
   1. Monitor detects → pauses agent
   2. User sees red error on dashboard
   3. User fixes their DB
   4. Monitor detects DB is back (next 5-min check)
   5. Agent auto-resumes
   6. Catches up on missed emails
   
   Scenario C — High Error Rate:
   1. Monitor pauses agent
   2. Logs all errors
   3. Notifies user + admin email
   4. Admin reviews logs
   5. Manual restart after fix

7. ADMIN DASHBOARD (simple, /admin route):
   Protected by admin check (your email only)
   Shows:
   - Total active users
   - Total trial users
   - Total emails processed today
   - Any system-wide errors
   - Recent monitor logs
   - Quick action: restart specific user's agent

Verify monitor agent runs via Celery.
Test scenario A (expire a Gmail token manually and watch auto-detection).
```

---

## PROMPT 47 — Pricing + Features Pages

```
Please build the public-facing Pricing and Features pages.

=== PRICING PAGE (src/app/(marketing)/pricing/page.tsx) ===

1. HERO:
   "Simple, transparent pricing"
   "Start free for 7 days. No credit card. Cancel anytime."
   Toggle: Monthly / Annual (Annual = 2 months free — future feature, greyed out)

2. FREE TRIAL HIGHLIGHT BOX:
   Prominent box at top:
   "🎉 Start with a 7-day FREE trial"
   "Full access to all features. claude-sonnet-4-5 model. No credit card required."
   → "Start Free Trial →" navy button

3. PRICING CARDS (3 full-detail cards):
   
   STARTER — $19/month:
   Model: claude-haiku-3-5
   "Best for small businesses and freelancers"
   Features:
   ✓ 500 emails per month
   ✓ 1 agent (your choice)
   ✓ Auto email classification
   ✓ Reply draft creation
   ✓ Basic analytics dashboard
   ✓ Email templates
   ✓ Spam protection
   ✓ Email support
   ✗ Multiple Gmail accounts
   ✗ WhatsApp alerts
   ✗ Custom rules engine
   ✗ Team members
   
   PROFESSIONAL — $49/month (FEATURED):
   Model: claude-sonnet-4-5
   "Best for growing businesses"
   "Most Popular" badge
   Features:
   ✓ Unlimited emails
   ✓ All 4 agents (switch anytime)
   ✓ Auto email classification
   ✓ Auto-send replies (with approval)
   ✓ Advanced analytics + charts
   ✓ Custom rules engine
   ✓ WhatsApp escalation alerts
   ✓ Working hours configuration
   ✓ 2 Gmail accounts
   ✓ Priority email support
   ✗ Team members
   ✗ Own database
   ✗ API access
   
   ENTERPRISE — $99/month:
   Model: claude-sonnet-4-5
   "Best for agencies and enterprises"
   Features:
   ✓ Everything in Professional
   ✓ Unlimited Gmail accounts
   ✓ Team members (up to 5)
   ✓ Connect own database
   ✓ API access
   ✓ White glove onboarding
   ✓ Dedicated support
   ✓ Custom agent features (on request)
   ✓ Monthly improvement review

4. FEATURE COMPARISON TABLE:
   Full comparison table — rows are features, columns are plans
   ✓ / ✗ / limit number in each cell
   Sticky header as user scrolls

5. FAQ SECTION (pricing specific):
   - "When does my trial end?"
   - "What payment methods are accepted?"
   - "Can I switch plans?"
   - "What happens if I cancel?"
   - "Do you offer refunds?"
   - "Is there a discount for annual payment?"

6. MONEY BACK SECTION:
   "Questions about pricing?"
   → Email: hireaidigitalemployee@gmail.com
   Response time: "We reply within 24 hours"

=== FEATURES PAGE (src/app/(marketing)/features/page.tsx) ===

Deep-dive into all platform features with visuals:

1. Hero: "Every feature your inbox needs"

2. Feature deep-dives (one section per major feature):
   - Smart Email Classification (with category examples)
   - AI Reply Generation (with before/after example)
   - Safety System (list of what agent never does)
   - Industry Agents (4 agents with what each handles)
   - Custom Rules Engine (IF/THEN visual example)
   - Analytics Dashboard (dashboard screenshot)
   - WhatsApp Integration (mock notification)
   - Security (encryption, audit logs)
   - Self-Healing (uptime guarantee)
   - Support Chatbot (chat preview)

3. Bottom CTA → Start free trial

Both pages: fully responsive, both themes, consistent with rest of site.
```

---

## PROMPT 48 — Theme System + Final Polish

```
Please implement the complete theme system and do final polish across the entire platform.

1. THEME SYSTEM:
   Using next-themes package (already installed).
   
   ThemeProvider setup in src/app/layout.tsx:
   - attribute="class"
   - defaultTheme="light"
   - enableSystem={false}
   - storageKey="hireai-theme"
   
   Theme Toggle Button (already built in Prompt 37):
   - Place in: Navbar (marketing), Dashboard header, Auth pages
   - Smooth icon transition: ☀️ ↔ 🌙
   - No flash on page load (suppressHydrationWarning)
   
   CSS Variables in globals.css:
   
   Light theme (default):
   --bg: #FFFFFF
   --bg-1: #FAFAFA
   --bg-2: #F4F4F5
   --bg-3: #EEEEEF
   --border: #E4E4E7
   --border-2: #D4D4D8
   --text: #09090B
   --text-2: #3F3F46
   --text-3: #71717A
   --text-4: #A1A1AA
   --navy: #1D4ED8
   --navy-hover: #1E40AF
   --navy-light: #DBEAFE
   --success: #16A34A
   --success-light: #DCFCE7
   --warning: #D97706
   --danger: #DC2626
   
   Dark theme (.dark class):
   --bg: #0A0A0A
   --bg-1: #111111
   --bg-2: #161616
   --bg-3: #1C1C1C
   --border: #242424
   --border-2: #2E2E2E
   --text: #FAFAFA
   --text-2: #E4E4E7
   --text-3: #A1A1AA
   --text-4: #71717A
   --navy: #2563EB
   --navy-hover: #3B82F6
   --navy-light: rgba(29,78,216,0.15)
   --success: #22C55E
   --success-light: rgba(34,197,94,0.1)
   --warning: #F59E0B
   --danger: #EF4444

   All components use CSS variables — NEVER hardcoded colors.
   Verify every page looks perfect in both themes.

2. ANIMATIONS + MICRO-INTERACTIONS:
   Using framer-motion throughout:
   
   Page transitions:
   - Route changes: fade in 0.2s
   
   Scroll animations (all marketing sections):
   - Fade up + slight Y movement
   - Stagger children with 0.06s delay
   
   Micro-interactions:
   - Button hover: slight scale + shadow
   - Card hover: subtle lift + border highlight
   - Agent card selection: smooth border + background transition
   - Stats counter: count up animation on scroll into view
   - Chatbot open: slide up from bottom
   - Sidebar collapse: smooth width transition
   - Modal: fade + scale from center
   - Toast notifications: slide in from top-right

3. MOBILE RESPONSIVENESS:
   All breakpoints:
   - Mobile: < 640px
   - Tablet: 640px - 1024px
   - Desktop: > 1024px
   
   Mobile changes:
   - Navbar → hamburger menu
   - Dashboard sidebar → bottom tab bar on mobile
   - Metrics grid → 2x2 on tablet, 1 column on mobile
   - Feature grid → 1 column on mobile
   - Pricing cards → stacked on mobile
   - Hero text → smaller font sizes

4. SEO + METADATA:
   src/app/layout.tsx metadata:
   - title: "HireAI — Intelligent Email Agents"
   - description: "AI agents that read, classify, and respond to your emails automatically"
   - keywords: AI email, email automation, Gmail agent, HR agent
   - og:image (create a simple OG image)
   - Twitter card

5. PERFORMANCE:
   - All images: next/image with proper sizing
   - Fonts: next/font (Geist) — no layout shift
   - Dynamic imports for heavy components (recharts, framer-motion)
   - Loading states everywhere (skeleton loaders)
   - Error boundaries for each major section

6. ACCESSIBILITY:
   - All interactive elements: keyboard navigable
   - Focus rings visible
   - ARIA labels on icon buttons
   - Color contrast ratios passing WCAG AA
   - Screen reader friendly

7. ERROR HANDLING:
   - 404 page (src/app/not-found.tsx): "Page not found" with back to home
   - Error page (src/app/error.tsx): "Something went wrong" with retry
   - API errors: toast notifications with clear messages
   - Network offline: show offline banner

8. FINAL CHECKLIST:
   □ Landing page loads under 3 seconds
   □ All links work correctly
   □ Theme toggle works on every page
   □ Mobile layout tested on 375px width
   □ Dashboard redirects if not logged in
   □ Login redirects to dashboard if already logged in
   □ Setup wizard shows on first login only
   □ All API calls have error handling
   □ Console has no errors
   □ Both themes look professional

Run npm run build — must complete with 0 errors.
Fix any TypeScript errors or build warnings.
```

---

## PROMPT 49 — FastAPI Integration + New Endpoints

```
Please add all missing FastAPI endpoints needed by the Next.js frontend.

Open the existing FastAPI project at:
/mnt/e/Digital_AI_WorkForce/hireai-gmailmind/

Add these new endpoints (create new files where appropriate):

=== DASHBOARD ENDPOINTS ===

GET /api/dashboard/stats
Response: {
  emails_today: int,
  auto_replied_today: int,
  escalated_today: int,
  avg_response_time: float,
  emails_yesterday: int,
  auto_replied_yesterday: int,
  agent_uptime_hours: float,
  emails_in_queue: int
}

GET /api/emails/recent?limit=10&page=1&category=all&action=all&search=
Response: {
  emails: [...],
  total: int,
  page: int,
  pages: int
}

GET /api/agent/status
Response: {
  is_running: bool,
  is_paused: bool,
  test_mode: bool,
  agent_type: str,
  tier: str,
  model: str,
  gmail_connected: str,
  gmail_valid: bool,
  last_processed: datetime,
  last_error: str | null
}

GET /api/analytics?period=week
Response: { daily_data: [...], categories: {...}, actions: {...}, top_senders: [...] }

=== AGENT CONFIG ENDPOINTS ===

GET  /api/agent/config
PATCH /api/agent/config
Body: {
  business_name, your_name, reply_language, reply_tone,
  working_hours_from, working_hours_to, working_days,
  blacklist_emails, whitelist_emails, blocked_keywords,
  whatsapp_number, escalation_keywords,
  test_mode, auto_send, max_emails_per_day, review_before_send
}

POST /api/agent/pause
POST /api/agent/resume
POST /api/agent/restart
POST /api/agent/force-sync

=== GMAIL ENDPOINTS ===

GET  /api/gmail/status
POST /api/gmail/connect    — Stores Gmail credentials
POST /api/gmail/reconnect  — Refresh token
DELETE /api/gmail/disconnect

=== USER/AUTH ENDPOINTS ===

GET  /api/user/profile
PATCH /api/user/profile
GET  /api/user/setup-status
POST /api/user/complete-setup

=== HEALTH ENDPOINTS ===

GET /api/health/platform  — { status: "operational", uptime: float }
GET /api/health/user      — User specific health check

=== SUPPORT ENDPOINTS ===

POST /api/support/chat
Body: { message: str, conversation_history: list, user_id: str }
Response: { reply: str, suggestions: list }

=== REVIEW ENDPOINTS ===

POST /api/reviews
GET  /api/reviews/public?limit=10&sort=rating
GET  /api/reviews/mine

=== BILLING ENDPOINTS ===

GET  /api/billing/plan
GET  /api/billing/history
POST /api/billing/change-plan
POST /api/billing/cancel

=== DATABASE CONFIG ===

POST /api/settings/database/test   — Test custom DB connection
POST /api/settings/database/connect
DELETE /api/settings/database/disconnect

For each endpoint:
1. Create the route
2. Add proper authentication check
3. Add error handling
4. Return proper HTTP status codes
5. Test with curl or httpie

Run all existing tests after adding endpoints:
python -m pytest tests/ -v --tb=short

Should still pass 267/267.
Add new tests for new endpoints.
```

---

## PROMPT 50 — Testing + Git + Deployment Prep

```
Please do complete testing, git commit, and deployment preparation.

=== PART 1: TESTING ===

1. Run Next.js build:
   cd /mnt/e/Digital_AI_WorkForce/hireai-frontend/
   npm run build
   Fix ALL TypeScript errors and build warnings.
   Build must complete successfully.

2. Test all pages manually:
   npm run dev
   
   Check each page:
   □ http://localhost:3000 — Landing page loads
   □ http://localhost:3000/pricing — Pricing page
   □ http://localhost:3000/features — Features page
   □ http://localhost:3000/login — Login page
   □ http://localhost:3000/signup — Signup page
   □ http://localhost:3000/dashboard — Redirects to login (if not authed)
   □ Theme toggle works on all pages
   □ Mobile layout at 375px width
   □ Both light and dark themes look correct

3. Run FastAPI tests:
   cd /mnt/e/Digital_AI_WorkForce/hireai-gmailmind/
   python -m pytest tests/ -v --tb=short
   All tests must pass.

4. Test API integration:
   - Start FastAPI: docker-compose up -d
   - Start Next.js: npm run dev
   - Test: Landing page chatbot works
   - Test: Dashboard stats load from API
   - Test: Agent status shows correctly

=== PART 2: GIT COMMIT ===

5. Commit FastAPI changes:
   cd /mnt/e/Digital_AI_WorkForce/hireai-gmailmind/
   git add .
   git commit -m "Phase 4 - New API endpoints for Next.js frontend"
   git push

6. Initialize git for frontend:
   cd /mnt/e/Digital_AI_WorkForce/hireai-frontend/
   git init
   
   Create .gitignore:
   node_modules/
   .next/
   .env.local
   .env
   *.log
   
   git add .
   git commit -m "Phase 4 Complete - HireAI Next.js Frontend
   
   Features:
   - Landing page with full marketing sections
   - Auth (NextAuth + Google OAuth + Setup Wizard)
   - Dashboard (Overview, Agent, Emails, Analytics)
   - Settings (Profile, Notifications, Security, Custom DB)
   - Billing page with plan management
   - Review/Feedback system
   - AI Support Chatbot (Claude-powered)
   - Self-healing Monitor Agent
   - Light/Dark theme toggle
   - Fully responsive mobile layout"
   
   git remote add origin [your-github-repo-url]
   git push -u origin main

=== PART 3: DEPLOYMENT PREP ===

7. Create deployment configs:

   Vercel config (vercel.json):
   {
     "buildCommand": "npm run build",
     "outputDirectory": ".next",
     "framework": "nextjs",
     "env": {
       "NEXTAUTH_URL": "@nextauth_url",
       "NEXTAUTH_SECRET": "@nextauth_secret",
       "GOOGLE_CLIENT_ID": "@google_client_id",
       "GOOGLE_CLIENT_SECRET": "@google_client_secret",
       "DATABASE_URL": "@database_url",
       "NEXT_PUBLIC_API_URL": "@api_url"
     }
   }

   Docker config for FastAPI (already exists, verify):
   - docker-compose.yml working
   - All env vars from .env

8. Create PHASE4_COMPLETION_REPORT.md:
   # Phase 4 Completion Report
   
   Date: [date]
   Status: ✅ COMPLETE
   
   ## What Was Built:
   - Full Next.js 14 marketing site
   - Complete dashboard with all features
   - Auth system with Google OAuth
   - Setup wizard for new users
   - [list all features]
   
   ## Test Results:
   - Next.js build: ✅ 0 errors
   - FastAPI tests: ✅ 267/267 passing
   - Both themes: ✅ Working
   - Mobile responsive: ✅ Tested
   
   ## Deployment Ready:
   - Vercel config: ✅
   - Environment variables: ✅
   - Git committed: ✅
   
   ## Next Steps:
   - Phase 4.5: Stripe payment integration
   - Phase 5: Claude API migration (replace OpenAI)
   - Phase 6: Launch + marketing

Show final completion report.
Confirm Phase 4 is 100% complete.
```

---

## QUICK REFERENCE

### Model Settings (Remember Always!):
```
Free Trial  → claude-sonnet-4-5
Tier 1      → claude-haiku-3-5
Tier 2      → claude-sonnet-4-5
Tier 3      → claude-sonnet-4-5
Support Bot → claude-haiku-3-5 (fast + cheap)
```

### Key URLs:
```
Landing:    http://localhost:3000
Dashboard:  http://localhost:3000/dashboard
FastAPI:    http://localhost:8000
API Docs:   http://localhost:8000/docs
```

### Design System:
```
Font:        Geist
Navy:        #1D4ED8
Dark BG:     #0A0A0A
Light BG:    #FFFFFF
Theme:       User toggleable (next-themes)
```

### Contact:
```
Email: hireaidigitalemployee@gmail.com
```

---

## HOW TO USE THESE PROMPTS IN CLAUDE CODE

```bash
# Step 1: Open Claude Code in terminal
cd /mnt/e/Digital_AI_WorkForce/

# Step 2: Read context files first
Please read:
- hireai-gmailmind/PHASE3_PROMPTS.md (to understand what's built)
- hireai-gmailmind/PHASE3_COMPLETION_REPORT.md (current state)
- PHASE4_PROMPTS.md (this file — what to build)

After reading, confirm understanding. Then wait for "Implement Prompt 36".

# Step 3: Implement one prompt at a time
"Now implement Prompt 36"
(Wait for completion)
"Now implement Prompt 37"
... and so on

# Step 4: Never skip prompts
Each prompt builds on the previous one.
Always confirm completion before moving to next.
```

---

*Phase 4 — HireAI Platform*  
*Next.js + FastAPI + All Features*  
*Total Prompts: 36–50 (15 prompts)*  
*Expected Outcome: Production-ready SaaS platform*
