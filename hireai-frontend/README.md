# HireAI Frontend

Next.js 14 frontend application for the HireAI platform.

## Tech Stack

- **Framework:** Next.js 14 with App Router
- **Language:** TypeScript
- **Styling:** Tailwind CSS
- **Theme:** Light/Dark mode support (next-themes)
- **Auth:** NextAuth.js with Google OAuth
- **State Management:** React Query (TanStack Query)
- **UI Components:** Radix UI primitives
- **Charts:** Recharts
- **Animations:** Framer Motion
- **Icons:** Lucide React

## Design System

- **Font:** Geist (variable font)
- **Primary Color:** Navy Blue (#1D4ED8)
- **Dark Background:** #0A0A0A
- **Light Background:** #FFFFFF
- **Style:** Clean, minimal (inspired by Linear.app and Claude.ai)

## Project Structure

```
src/
├── app/
│   ├── (marketing)/          # Public pages
│   │   ├── page.tsx          # Landing page
│   │   ├── pricing/
│   │   └── features/
│   ├── (auth)/               # Auth pages
│   │   ├── login/
│   │   └── signup/
│   ├── dashboard/            # Protected dashboard
│   │   ├── page.tsx          # Overview
│   │   ├── agent/
│   │   ├── emails/
│   │   ├── analytics/
│   │   ├── settings/
│   │   ├── billing/
│   │   └── gmail/
│   ├── api/
│   │   └── auth/[...nextauth]/
│   ├── layout.tsx
│   └── globals.css
├── components/
│   ├── ui/                   # Reusable UI components
│   ├── marketing/            # Landing page components
│   ├── dashboard/            # Dashboard components
│   └── shared/               # Shared components
├── lib/
│   ├── api.ts                # Axios instance
│   ├── utils.ts              # Helper functions
│   └── auth.ts               # NextAuth config
├── hooks/                    # Custom React hooks
├── types/                    # TypeScript definitions
└── store/                    # State management
```

## Environment Variables

Copy `.env.local.example` to `.env.local` and fill in your values:

```bash
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-here
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
DATABASE_URL=your-neon-db-url
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## Development

```bash
# Install dependencies
npm install

# Run development server
npm run dev

# Build for production
npm run build

# Start production server
npm start

# Lint code
npm run lint
```

## Features to Implement (Phase 4)

- ✅ Project Setup Complete
- ⏳ Design System + UI Components (Prompt 37)
- ⏳ Landing Page (Prompt 38)
- ⏳ Auth System (Prompt 39)
- ⏳ Dashboard Pages (Prompts 40-42)
- ⏳ Settings + Billing (Prompt 43)
- ⏳ Review System (Prompt 44)
- ⏳ AI Support Chatbot (Prompt 45)
- ⏳ Self-Healing Monitor (Prompt 46)
- ⏳ Pricing + Features Pages (Prompt 47)
- ⏳ Theme System + Polish (Prompt 48)
- ⏳ FastAPI Integration (Prompt 49)
- ⏳ Testing + Deployment (Prompt 50)

## Backend API

The frontend connects to the FastAPI backend at `http://localhost:8000`

Backend project location: `/mnt/e/Digital_AI_WorkForce/hireai-gmailmind/`

## Notes

- Supports both Light and Dark themes
- Fully responsive (mobile, tablet, desktop)
- TypeScript strict mode enabled
- ESLint configured for Next.js
- Tailwind CSS with custom design tokens
<!-- Vercel deployment trigger -->
