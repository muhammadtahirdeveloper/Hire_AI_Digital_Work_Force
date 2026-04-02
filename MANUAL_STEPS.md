# HireAI — Manual Setup Steps

These are steps you must complete manually (code cannot do them for you).

---

## 1. Lemon Squeezy Setup

1. **Create account** at [lemonsqueezy.com](https://lemonsqueezy.com)
2. **Create a Store** in the Lemon Squeezy dashboard
3. **Create 3 Products** with these names and prices:
   - **Starter** — $19/month (or your preferred price)
   - **Professional** — $49/month
   - **Enterprise** — $99/month
4. **Copy the Variant ID** for each product (found in Product → Variants)
5. **Generate an API Key**: Settings → API Keys → Create
6. **Setup Webhook**:
   - URL: `https://<your-backend-domain>/api/webhooks/lemonsqueezy`
   - Events to select:
     - `subscription_created`
     - `subscription_updated`
     - `subscription_cancelled`
     - `subscription_payment_success`
     - `subscription_payment_failed`
7. **Copy the Webhook Signing Secret** from the webhook settings
8. **Add these env vars** to your backend (Railway):
   ```
   LEMON_SQUEEZY_API_KEY=your_api_key
   LEMON_SQUEEZY_STORE_ID=your_store_id
   LEMON_SQUEEZY_WEBHOOK_SECRET=your_webhook_secret
   LEMON_SQUEEZY_STARTER_VARIANT_ID=variant_id_for_starter
   LEMON_SQUEEZY_PRO_VARIANT_ID=variant_id_for_professional
   LEMON_SQUEEZY_ENTERPRISE_VARIANT_ID=variant_id_for_enterprise
   ```

---

## 2. Supabase Setup

1. **Create a project** at [supabase.com](https://supabase.com)
2. **Enable Google OAuth** provider:
   - Supabase Dashboard → Authentication → Providers → Google
   - Add your Google Client ID and Client Secret
3. **Get credentials** from Supabase → Settings → API:
   - Project URL (`NEXT_PUBLIC_SUPABASE_URL`)
   - Anon/public key (`NEXT_PUBLIC_SUPABASE_ANON_KEY`)
   - Service Role key (`SUPABASE_SERVICE_ROLE_KEY`)
   - JWT Secret: Settings → API → JWT Settings (`SUPABASE_JWT_SECRET`)
4. **Add redirect URL** in Supabase → Authentication → URL Configuration:
   - `https://<your-frontend-domain>/api/auth/callback`
   - For local dev: `http://localhost:3000/api/auth/callback`
5. **Add these env vars** to your frontend (Vercel):
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your_anon_key
   ```
6. **Add these env vars** to your backend (Railway):
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   SUPABASE_JWT_SECRET=your_jwt_secret
   ```

---

## 3. Google Cloud Console

1. **Add Supabase callback URL** to authorized redirect URIs:
   - Go to Google Cloud Console → APIs & Services → Credentials
   - Edit your OAuth 2.0 Client ID
   - Add: `https://<your-supabase-project>.supabase.co/auth/v1/callback`
2. **Keep existing** Gmail API scopes (no changes needed)

---

## 4. Deployment (Railway + Vercel)

### Backend (Railway)
Add all new env vars:
```
# Supabase
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=

# Lemon Squeezy
LEMON_SQUEEZY_API_KEY=
LEMON_SQUEEZY_STORE_ID=
LEMON_SQUEEZY_WEBHOOK_SECRET=
LEMON_SQUEEZY_STARTER_VARIANT_ID=
LEMON_SQUEEZY_PRO_VARIANT_ID=
LEMON_SQUEEZY_ENTERPRISE_VARIANT_ID=
```

### Frontend (Vercel)
Add new env vars:
```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
```

Remove old env vars (no longer needed):
```
NEXTAUTH_SECRET
NEXTAUTH_URL
```

---

## 5. Testing Checklist

- [ ] Sign up via Supabase Google OAuth → user syncs to backend DB
- [ ] Sign up via email/password → user created in Supabase + backend DB
- [ ] Login works and session persists across page refreshes
- [ ] Lemon Squeezy test mode checkout creates a subscription
- [ ] Webhook fires and updates subscriptions table
- [ ] Billing page shows real subscription data
- [ ] Cancel subscription works
- [ ] Customer portal opens correctly
- [ ] Reviews page shows empty state (no fake data)
- [ ] Dashboard loads with Supabase auth
- [ ] Switch to Lemon Squeezy live mode when ready for production

---

## 6. Adding New Agents (Future)

The architecture supports adding new agents easily:

1. Create folder: `agents/<name>/`
2. Create agent file extending `BaseAgent`
3. Implement: `get_system_prompt()`, `get_available_tools()`, `classify_email()`
4. Create skills file: `agents/<name>/<name>_skills.py`
5. Register in `orchestrator.py`: `self.registry.register("<name>", YourAgent)`
6. Add to `VALID_INDUSTRIES` in `user_router.py`
7. Add tier features in `feature_gates.py`
8. Add frontend card in setup wizard
9. Write tests

No core architecture changes needed.
