// NextAuth has been replaced by Supabase Auth.
// This route is kept to avoid 404s for any lingering redirects.
import { NextResponse } from "next/server";

export async function GET() {
  return NextResponse.redirect(new URL("/login", process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000"));
}

export async function POST() {
  return NextResponse.json({ error: "Auth has moved to Supabase" }, { status: 410 });
}
