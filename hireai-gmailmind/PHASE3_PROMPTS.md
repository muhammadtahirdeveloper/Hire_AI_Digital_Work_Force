# GmailMind — Phase 3 Claude Code Prompts (27-35)
# Real Estate Agent + E-commerce Agent

---

## WHAT IS PHASE 3?
Phase 3 adds two new industry-specific agents to GmailMind:
1. **Real Estate Agent** — handles property inquiries, viewings, landlord/tenant emails
2. **E-commerce Agent** — handles orders, refunds, customer support, supplier emails

Both agents follow the EXACT same pattern as HRAgent.
The Orchestrator will automatically route users to the correct agent
based on their industry setting.

## HOW TO USE THESE PROMPTS
1. Open hireai-gmailmind/ project in Claude Code
2. First say:
   "Please read PHASE2_PROMPTS.md, PHASE2.5_PROMPTS.md, and PHASE3_PROMPTS.md"
3. Then say: "Now implement Prompt 27"
4. Verify → git commit → then say "Now implement Prompt 28"
5. Continue until Prompt 35

## IMPORTANT RULES FOR CLAUDE CODE
- Do NOT break any existing Phase 1, 2, or 2.5 features
- Do NOT change existing database tables
- Follow EXACT same pattern as HRAgent
- All new agents must extend BaseAgent
- Register new agents in AgentRegistry
- Test after every prompt before moving to next

---

## PROMPT 27 — REAL ESTATE AGENT

```
Please read PHASE2_PROMPTS.md, PHASE2.5_PROMPTS.md, and PHASE3_PROMPTS.md first.

Now implement Prompt 27: Real Estate Agent

Create these files following the EXACT same pattern as agents/hr/hr_agent.py:

1. agents/real_estate/__init__.py
   Empty file.

2. agents/real_estate/real_estate_templates.py
   REAL_ESTATE_TEMPLATES dictionary:

   'property_inquiry_reply': """
   Dear {client_name},

   Thank you for your interest in {property_address}.

   Here are the key details:
   - Price: {price}
   - Size: {size}
   - Bedrooms: {bedrooms}
   - Location: {location}

   I would be happy to arrange a viewing at your convenience.
   Please let me know your availability and I will confirm a slot.

   Best regards,
   {agent_name}
   {company_name}
   """

   'viewing_confirmation': """
   Dear {client_name},

   Your property viewing has been confirmed:

   Property: {property_address}
   Date: {viewing_date}
   Time: {viewing_time}
   Agent: {agent_name}

   Please bring a valid ID for the viewing.
   If you need to reschedule, please contact us at least 24 hours in advance.

   Looking forward to meeting you!

   Best regards,
   {agent_name}
   {company_name}
   """

   'rental_application_received': """
   Dear {applicant_name},

   Thank you for submitting your rental application for {property_address}.

   We have received your application and will review it within 2-3 business days.
   We will contact you shortly with an update.

   Best regards,
   {agent_name}
   {company_name}
   """

   'maintenance_request_received': """
   Dear {tenant_name},

   We have received your maintenance request regarding: {issue_description}

   Property: {property_address}
   Request ID: {request_id}
   Priority: {priority}

   Our team will be in touch within {response_time} to schedule the repair.

   Best regards,
   {company_name} Property Management
   """

   'offer_received': """
   Dear {seller_name},

   We have received an offer on your property at {property_address}:

   Offered Price: {offer_price}
   Offered By: {buyer_name}
   Offer Valid Until: {valid_until}

   Please review and let us know if you would like to accept, counter, or decline.

   Best regards,
   {agent_name}
   {company_name}
   """

   'lease_renewal_reminder': """
   Dear {tenant_name},

   This is a friendly reminder that your lease for {property_address}
   is due to expire on {expiry_date}.

   We would love to have you continue as our tenant.
   Please let us know if you would like to renew your lease.

   Current Rent: {current_rent}
   Proposed New Rent: {new_rent}

   Please respond by {response_deadline} to secure your tenancy.

   Best regards,
   {company_name} Property Management
   """

3. agents/real_estate/property_tracker.py
   PropertyTracker class:

   get_property(user_id: str, property_address: str) -> dict or None:
   Read from properties table (to be created in Prompt 29).

   log_inquiry(user_id: str, client_email: str, property_address: str, inquiry_type: str) -> int:
   Insert into property_inquiries table.
   Return inquiry id.

   log_viewing(user_id: str, client_email: str, property_address: str,
               viewing_date: str, viewing_time: str) -> int:
   Insert into property_viewings table.
   Return viewing id.

   get_active_listings(user_id: str) -> list:
   Return all active properties for this user.

   get_inquiry_summary(user_id: str) -> dict:
   Returns: {total_inquiries: int, viewings_scheduled: int,
             offers_received: int, properties_listed: int}

4. agents/real_estate/real_estate_agent.py
   RealEstateAgent(BaseAgent) class — follow EXACT same pattern as HRAgent:

   agent_name = "GmailMind Real Estate Agent"
   industry = "real_estate"
   supported_tiers = ["tier2", "tier3"]

   _REAL_ESTATE_CATEGORIES = {
     "property_inquiry": [
       r"interested in", r"property", r"viewing", r"visit",
       r"available", r"for sale", r"for rent", r"listing",
       r"how much", r"price", r"bedroom", r"apartment", r"house",
     ],
     "viewing_request": [
       r"schedule.*viewing", r"book.*viewing", r"arrange.*visit",
       r"can i see", r"want to view", r"viewing.*available",
       r"show.*property", r"visit.*property",
     ],
     "rental_application": [
       r"rental application", r"apply.*rent", r"tenant application",
       r"application form", r"documents.*rent", r"references",
     ],
     "maintenance_request": [
       r"repair", r"broken", r"not working", r"maintenance",
       r"leak", r"damage", r"fix", r"issue with", r"problem with",
       r"heating", r"plumbing", r"electrical",
     ],
     "offer_submission": [
       r"offer", r"willing to pay", r"bid", r"purchase price",
       r"offer.*property", r"make an offer",
     ],
     "lease_inquiry": [
       r"lease", r"contract", r"tenancy", r"agreement",
       r"renew", r"renewal", r"end of lease",
     ],
     "landlord_message": [
       r"landlord", r"owner", r"property manager",
       r"rent.*increase", r"notice", r"eviction",
     ],
   }

   get_system_prompt(tier) -> str:
   Return:
   "You are an expert real estate email assistant.
    You help real estate agents and property managers handle
    property inquiries, schedule viewings, process rental applications,
    and manage tenant communications professionally.
    Always be helpful, responsive, and professional.
    For property inquiries, highlight key features and suggest viewings.
    For maintenance requests, acknowledge urgency and set clear timelines."

   get_available_tools(tier) -> list:
   tier2: ['read_emails', 'label_email', 'search_emails',
           'reply_to_email', 'create_draft', 'send_escalation_alert',
           'schedule_followup', 'create_calendar_event']
   tier3: tier2 + ['send_email', 'get_crm_contact', 'update_crm']

   classify_email(email) -> str:
   Same pattern as HRAgent._HR_CATEGORIES matching.
   Use _REAL_ESTATE_CATEGORIES.
   Return category string or "other".

   process_email(email, user_config, tier, user_id) -> dict:
   Same structure as HRAgent.process_email():

   If category == "property_inquiry":
     1. Log inquiry using PropertyTracker
     2. Draft reply using 'property_inquiry_reply' template
     3. Return action dict

   If category == "viewing_request":
     1. Log viewing request
     2. Find available calendar slots
     3. Draft viewing_confirmation template with slots
     4. Return action dict

   If category == "rental_application":
     1. Log application
     2. Send 'rental_application_received' reply
     3. Return action dict

   If category == "maintenance_request":
     1. Detect urgency (use skills/base_skills.py detect_urgency)
     2. Log maintenance request
     3. Send 'maintenance_request_received' reply
     4. If urgency == 'critical': send escalation alert
     5. Return action dict

   If category == "offer_submission":
     1. Log offer
     2. Draft 'offer_received' template for agent review
     3. Return action dict

   Default: label and archive.

5. Register RealEstateAgent in orchestrator/orchestrator.py __init__:
   from agents.real_estate.real_estate_agent import RealEstateAgent
   self.registry.register('real_estate', RealEstateAgent)

Verify with:
python -c "
from agents.real_estate.real_estate_agent import RealEstateAgent
a = RealEstateAgent()
print('Agent:', a.agent_name)
print('Industry:', a.industry)
test_email = {'subject': 'Interested in your property', 'body': 'I want to view the apartment'}
print('Category:', a.classify_email(test_email))
print('Prompt 27 Real Estate Agent: OK')
"
```

---

## PROMPT 28 — E-COMMERCE AGENT

```
Implement Prompt 28: E-commerce Agent

Create these files following the EXACT same pattern as HRAgent:

1. agents/ecommerce/__init__.py
   Empty file.

2. agents/ecommerce/ecommerce_templates.py
   ECOMMERCE_TEMPLATES dictionary:

   'order_confirmation': """
   Dear {customer_name},

   Thank you for your order!

   Order Details:
   - Order ID: {order_id}
   - Items: {items}
   - Total: {total_amount}
   - Estimated Delivery: {delivery_date}

   We will send you a tracking number once your order is shipped.

   Thank you for shopping with us!

   Best regards,
   {company_name} Team
   """

   'refund_initiated': """
   Dear {customer_name},

   We have initiated your refund for Order #{order_id}.

   Refund Amount: {refund_amount}
   Reason: {reason}
   Processing Time: 3-5 business days

   The amount will be credited to your original payment method.
   If you have any questions, please don't hesitate to contact us.

   Best regards,
   {company_name} Support Team
   """

   'complaint_acknowledged': """
   Dear {customer_name},

   Thank you for bringing this to our attention.

   We have received your complaint regarding: {complaint_description}
   Reference Number: {reference_id}

   Our team is investigating this matter and will respond within 24 hours.
   We sincerely apologize for any inconvenience caused.

   Best regards,
   {company_name} Support Team
   """

   'shipping_update': """
   Dear {customer_name},

   Your order #{order_id} has been {shipping_status}.

   Tracking Number: {tracking_number}
   Estimated Delivery: {delivery_date}
   Carrier: {carrier}

   You can track your package at: {tracking_url}

   Best regards,
   {company_name} Team
   """

   'supplier_acknowledgment': """
   Dear {supplier_name},

   Thank you for your message regarding {subject}.

   We have noted your update and will process it accordingly.
   Our team will be in touch within 1-2 business days.

   Best regards,
   {company_name} Procurement Team
   """

   'review_request': """
   Dear {customer_name},

   We hope you are enjoying your recent purchase from {company_name}!

   We would love to hear your feedback.
   Please take a moment to leave a review — it helps us improve
   and helps other customers make informed decisions.

   Thank you for your support!

   Best regards,
   {company_name} Team
   """

3. agents/ecommerce/order_tracker.py
   OrderTracker class:

   log_order_inquiry(user_id: str, customer_email: str,
                     order_id: str, inquiry_type: str) -> int:
   Insert into order_inquiries table (created in Prompt 30).
   Return inquiry id.

   log_refund_request(user_id: str, customer_email: str,
                      order_id: str, reason: str) -> int:
   Insert into refund_requests table.
   Return refund id.

   log_complaint(user_id: str, customer_email: str,
                 description: str, priority: str) -> int:
   Insert into customer_complaints table.
   Return complaint id.

   get_support_summary(user_id: str) -> dict:
   Returns: {
     total_inquiries: int,
     pending_refunds: int,
     open_complaints: int,
     resolved_today: int
   }

   extract_order_id(text: str) -> str or None:
   Use regex to find order ID patterns like:
   #12345, ORDER-12345, ORD-12345
   Return order id string or None.

4. agents/ecommerce/ecommerce_agent.py
   EcommerceAgent(BaseAgent) class — follow EXACT same pattern as HRAgent:

   agent_name = "GmailMind E-commerce Agent"
   industry = "ecommerce"
   supported_tiers = ["tier2", "tier3"]

   _ECOMMERCE_CATEGORIES = {
     "order_inquiry": [
       r"order", r"order.*status", r"where.*order",
       r"track.*order", r"order.*number", r"purchase",
       r"order.*confirmation", r"when.*arrive", r"delivery",
     ],
     "refund_request": [
       r"refund", r"return", r"money back", r"cancel.*order",
       r"want.*refund", r"charge.*wrong", r"incorrect.*charge",
       r"not.*received", r"damaged", r"defective",
     ],
     "complaint": [
       r"complaint", r"unhappy", r"disappointed", r"terrible",
       r"worst", r"problem with", r"issue with", r"not working",
       r"broken", r"wrong.*item", r"missing.*item",
     ],
     "shipping_inquiry": [
       r"shipping", r"delivery", r"tracking", r"dispatch",
       r"shipped", r"courier", r"package", r"parcel",
       r"when.*deliver", r"track.*package",
     ],
     "supplier_email": [
       r"invoice", r"stock", r"inventory", r"supply",
       r"wholesale", r"bulk order", r"restock", r"purchase order",
       r"payment.*due", r"outstanding.*payment",
     ],
     "product_inquiry": [
       r"product", r"item", r"available", r"in stock",
       r"price", r"discount", r"offer", r"specifications",
       r"size", r"color", r"variant",
     ],
     "review_feedback": [
       r"review", r"feedback", r"rating", r"experience",
       r"recommend", r"happy.*with", r"satisfied",
     ],
   }

   get_system_prompt(tier) -> str:
   Return:
   "You are an expert e-commerce customer support email assistant.
    You help online businesses handle customer inquiries, process
    refund requests, resolve complaints, and manage supplier emails.
    Always be empathetic, solution-focused, and professional.
    For complaints: acknowledge first, then solve.
    For refunds: be clear about the process and timeline.
    For order inquiries: provide accurate and helpful information."

   get_available_tools(tier) -> list:
   tier2: ['read_emails', 'label_email', 'search_emails',
           'reply_to_email', 'create_draft', 'send_escalation_alert',
           'schedule_followup']
   tier3: tier2 + ['send_email', 'get_crm_contact', 'update_crm']

   classify_email(email) -> str:
   Same pattern as HRAgent matching using _ECOMMERCE_CATEGORIES.
   Return category string or "other".

   process_email(email, user_config, tier, user_id) -> dict:

   If category == "order_inquiry":
     1. Extract order ID from email body
     2. Log inquiry using OrderTracker
     3. Draft 'order_confirmation' reply
     4. Return action dict

   If category == "refund_request":
     1. Extract order ID
     2. Log refund request using OrderTracker
     3. Draft 'refund_initiated' reply
     4. Return action dict

   If category == "complaint":
     1. Detect urgency using base_skills
     2. Log complaint using OrderTracker
     3. Draft 'complaint_acknowledged' reply
     4. If urgency == 'critical': send escalation alert
     5. Return action dict

   If category == "shipping_inquiry":
     1. Log inquiry
     2. Draft 'shipping_update' reply
     3. Return action dict

   If category == "supplier_email":
     1. Label as SUPPLIER
     2. Draft 'supplier_acknowledgment' reply
     3. Return action dict

   If category == "review_feedback":
     1. Label appropriately
     2. If positive: archive
     3. If negative: escalate
     4. Return action dict

   Default: label and archive.

5. Register EcommerceAgent in orchestrator/orchestrator.py __init__:
   from agents.ecommerce.ecommerce_agent import EcommerceAgent
   self.registry.register('ecommerce', EcommerceAgent)

Verify with:
python -c "
from agents.ecommerce.ecommerce_agent import EcommerceAgent
a = EcommerceAgent()
print('Agent:', a.agent_name)
print('Industry:', a.industry)
test_email = {'subject': 'Where is my order #12345?', 'body': 'I placed an order last week'}
print('Category:', a.classify_email(test_email))
refund_email = {'subject': 'I want a refund', 'body': 'The item arrived damaged'}
print('Refund Category:', a.classify_email(refund_email))
print('Prompt 28 E-commerce Agent: OK')
"
```

---

## PROMPT 29 — REAL ESTATE DATABASE SCHEMA

```
Implement Prompt 29: Real Estate Database Schema

Update scripts/setup_db.py to add Real Estate tables.

Add function create_real_estate_tables(engine) and call it from main():

1. properties table:
CREATE TABLE IF NOT EXISTS properties (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    address VARCHAR(500) NOT NULL,
    property_type VARCHAR(50) DEFAULT 'residential',
    status VARCHAR(50) DEFAULT 'available',
    price DECIMAL(12,2),
    bedrooms INTEGER DEFAULT 0,
    bathrooms INTEGER DEFAULT 0,
    size_sqft INTEGER DEFAULT 0,
    location VARCHAR(255),
    description TEXT,
    listing_type VARCHAR(20) DEFAULT 'sale',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

2. property_inquiries table:
CREATE TABLE IF NOT EXISTS property_inquiries (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    client_email VARCHAR(320) NOT NULL,
    property_address VARCHAR(500),
    inquiry_type VARCHAR(50) DEFAULT 'general',
    status VARCHAR(50) DEFAULT 'new',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

3. property_viewings table:
CREATE TABLE IF NOT EXISTS property_viewings (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    client_email VARCHAR(320) NOT NULL,
    property_address VARCHAR(500),
    viewing_date TIMESTAMP,
    status VARCHAR(50) DEFAULT 'scheduled',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

4. maintenance_requests table:
CREATE TABLE IF NOT EXISTS maintenance_requests (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    tenant_email VARCHAR(320) NOT NULL,
    property_address VARCHAR(500),
    issue_description TEXT,
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(50) DEFAULT 'open',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

Add indexes:
CREATE INDEX IF NOT EXISTS idx_properties_user_id ON properties(user_id);
CREATE INDEX IF NOT EXISTS idx_property_inquiries_user ON property_inquiries(user_id);
CREATE INDEX IF NOT EXISTS idx_property_viewings_user ON property_viewings(user_id);
CREATE INDEX IF NOT EXISTS idx_maintenance_user ON maintenance_requests(user_id);

Run and verify:
python scripts/setup_db.py

Expected output:
- properties table created
- property_inquiries table created
- property_viewings table created
- maintenance_requests table created
```

---

## PROMPT 30 — E-COMMERCE DATABASE SCHEMA

```
Implement Prompt 30: E-commerce Database Schema

Update scripts/setup_db.py to add E-commerce tables.

Add function create_ecommerce_tables(engine) and call it from main():

1. order_inquiries table:
CREATE TABLE IF NOT EXISTS order_inquiries (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    customer_email VARCHAR(320) NOT NULL,
    order_id VARCHAR(100),
    inquiry_type VARCHAR(50) DEFAULT 'general',
    status VARCHAR(50) DEFAULT 'open',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

2. refund_requests table:
CREATE TABLE IF NOT EXISTS refund_requests (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    customer_email VARCHAR(320) NOT NULL,
    order_id VARCHAR(100),
    reason TEXT,
    amount DECIMAL(10,2),
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

3. customer_complaints table:
CREATE TABLE IF NOT EXISTS customer_complaints (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    customer_email VARCHAR(320) NOT NULL,
    description TEXT,
    priority VARCHAR(20) DEFAULT 'medium',
    status VARCHAR(50) DEFAULT 'open',
    resolution TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

4. supplier_emails table:
CREATE TABLE IF NOT EXISTS supplier_emails (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    supplier_email VARCHAR(320) NOT NULL,
    subject VARCHAR(500),
    email_type VARCHAR(50) DEFAULT 'general',
    status VARCHAR(50) DEFAULT 'received',
    notes TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);

Add indexes:
CREATE INDEX IF NOT EXISTS idx_order_inquiries_user ON order_inquiries(user_id);
CREATE INDEX IF NOT EXISTS idx_refund_requests_user ON refund_requests(user_id);
CREATE INDEX IF NOT EXISTS idx_complaints_user ON customer_complaints(user_id);
CREATE INDEX IF NOT EXISTS idx_supplier_emails_user ON supplier_emails(user_id);

Run and verify:
python scripts/setup_db.py

Expected output:
- order_inquiries table created
- refund_requests table created
- customer_complaints table created
- supplier_emails table created
```

---

## PROMPT 31 — UPDATE ORCHESTRATOR & USER ROUTER

```
Implement Prompt 31: Update Orchestrator & User Router

Update industry routing to support new agents.

1. Update orchestrator/user_router.py:
   get_user_industry() should now support:
   - 'general' (existing)
   - 'hr' (existing)
   - 'real_estate' (NEW)
   - 'ecommerce' (NEW)

   Add VALID_INDUSTRIES list:
   VALID_INDUSTRIES = ['general', 'hr', 'real_estate', 'ecommerce']

   If industry from DB not in VALID_INDUSTRIES:
   Log warning and default to 'general'.

2. Update orchestrator/feature_gates.py:
   Add real_estate and ecommerce specific features to tier definitions:

   tier2 features add:
   - 'property_tracker'
   - 'viewing_scheduler'
   - 'order_tracker'
   - 'refund_manager'

   tier3 features add:
   - 'crm_sync'
   - 'advanced_analytics'
   - 'bulk_email'

3. Update orchestrator/orchestrator.py:
   In __init__ register all 4 agents:
   from agents.general.general_agent import GeneralAgent
   from agents.hr.hr_agent import HRAgent
   from agents.real_estate.real_estate_agent import RealEstateAgent
   from agents.ecommerce.ecommerce_agent import EcommerceAgent

   self.registry.register('general', GeneralAgent)
   self.registry.register('hr', HRAgent)
   self.registry.register('real_estate', RealEstateAgent)
   self.registry.register('ecommerce', EcommerceAgent)

4. Update api/routes/orchestrator_routes.py:
   GET /platform/agents
   Response: {
     registered_agents: ['general', 'hr', 'real_estate', 'ecommerce'],
     total: 4
   }

   Update POST /platform/users/{user_id}/setup to validate industry:
   Only allow: general, hr, real_estate, ecommerce
   Return 400 if invalid industry provided.

Verify with:
python -c "
from orchestrator.orchestrator import GmailMindOrchestrator
o = GmailMindOrchestrator()
industries = o.registry.list_industries()
assert 'real_estate' in industries
assert 'ecommerce' in industries
print('Registered agents:', industries)
print('Prompt 31 Orchestrator Update: OK')
"
```

---

## PROMPT 32 — API ROUTES FOR NEW AGENTS

```
Implement Prompt 32: Real Estate & E-commerce API Routes

1. Create api/routes/real_estate_routes.py:
   Router prefix: /real-estate

   GET /real-estate/{user_id}/inquiries
   Query params: status (optional), page=1, page_size=20
   Response: paginated list of property inquiries

   GET /real-estate/{user_id}/viewings
   Query params: days_ahead=7
   Response: list of upcoming viewings

   GET /real-estate/{user_id}/maintenance
   Query params: status (optional, default='open')
   Response: list of maintenance requests

   GET /real-estate/{user_id}/properties
   Response: list of active property listings

   POST /real-estate/{user_id}/properties
   Body: {address, property_type, price, bedrooms, location, listing_type}
   Response: {success: true, property_id: int}

   GET /real-estate/{user_id}/summary
   Response: {
     total_inquiries: int,
     viewings_scheduled: int,
     open_maintenance: int,
     properties_listed: int
   }

2. Create api/routes/ecommerce_routes.py:
   Router prefix: /ecommerce

   GET /ecommerce/{user_id}/inquiries
   Query params: inquiry_type (optional), page=1, page_size=20
   Response: paginated list of order inquiries

   GET /ecommerce/{user_id}/refunds
   Query params: status (optional, default='pending')
   Response: list of refund requests

   PUT /ecommerce/{user_id}/refunds/{refund_id}
   Body: {status: str}
   Response: {success: true, refund_id, new_status}

   GET /ecommerce/{user_id}/complaints
   Query params: priority (optional), status (optional)
   Response: list of customer complaints

   PUT /ecommerce/{user_id}/complaints/{complaint_id}
   Body: {status: str, resolution: str}
   Response: {success: true}

   GET /ecommerce/{user_id}/summary
   Response: {
     total_inquiries: int,
     pending_refunds: int,
     open_complaints: int,
     resolved_today: int
   }

3. Register both routers in api/main.py:
   from api.routes.real_estate_routes import router as real_estate_router
   from api.routes.ecommerce_routes import router as ecommerce_router
   app.include_router(real_estate_router)
   app.include_router(ecommerce_router)

Verify:
docker-compose up --build
Open http://localhost:8000/docs
New sections should appear: Real-estate, Ecommerce

Print: "Prompt 32 API Routes: OK"
```

---

## PROMPT 33 — INDUSTRY SKILLS EXTENSION

```
Implement Prompt 33: Industry-Specific Skills

1. Create skills/real_estate_skills.py:
   RealEstateSkills(BaseSkills) class:

   format_property_listing(property: dict) -> str:
   Returns formatted property description for emails.
   Example:
   "🏠 {address}
    💰 Price: {price}
    🛏 Bedrooms: {bedrooms} | 🚿 Bathrooms: {bathrooms}
    📐 Size: {size_sqft} sqft
    📍 Location: {location}"

   detect_maintenance_priority(description: str) -> str:
   Returns: 'low', 'medium', 'high', 'critical'
   Critical: ['flood', 'fire', 'gas leak', 'no electricity', 'no water', 'break-in']
   High: ['heating', 'no hot water', 'roof leak', 'broken lock']
   Medium: ['appliance', 'plumbing', 'pest']
   Low: everything else

   generate_weekly_property_report(user_id: str) -> dict:
   Query last 7 days from:
   - property_inquiries table
   - property_viewings table
   - maintenance_requests table
   Return comprehensive report dict.

   format_report_for_whatsapp(report: dict) -> str:
   "🏠 Weekly Property Report
    ========================
    📧 New Inquiries: {count}
    👁 Viewings Scheduled: {count}
    🔧 Maintenance Requests: {count}
    ✅ Resolved: {count}
    🏡 Active Listings: {count}"

2. Create skills/ecommerce_skills.py:
   EcommerceSkills(BaseSkills) class:

   extract_order_id(text: str) -> str or None:
   Regex patterns for order IDs:
   r'#(\d{4,10})', r'ORDER[-_](\w+)', r'ORD[-_](\w+)'
   Return first match or None.

   detect_customer_sentiment(email_body: str) -> str:
   Returns: 'positive', 'neutral', 'negative', 'very_negative'
   Very negative keywords: ['furious', 'outraged', 'legal', 'lawsuit', 'scam', 'fraud']
   Negative: ['disappointed', 'unhappy', 'terrible', 'worst', 'angry']
   Positive: ['happy', 'love', 'amazing', 'excellent', 'great']

   generate_weekly_ecommerce_report(user_id: str) -> dict:
   Query last 7 days from:
   - order_inquiries table
   - refund_requests table
   - customer_complaints table
   Return comprehensive report dict.

   format_report_for_whatsapp(report: dict) -> str:
   "🛒 Weekly E-commerce Report
    ===========================
    📧 Order Inquiries: {count}
    💸 Refund Requests: {count}
    😤 Complaints: {count}
    ✅ Resolved: {count}
    ⭐ Positive Reviews: {count}"

3. Update scheduler/tasks.py:
   Add new weekly report tasks:

   @app.task(name='scheduler.tasks.send_real_estate_weekly_report')
   def send_real_estate_weekly_report(user_id='default'):
     - Generate weekly RE report
     - Send via WhatsApp if configured
     - Log completion

   @app.task(name='scheduler.tasks.send_ecommerce_weekly_report')
   def send_ecommerce_weekly_report(user_id='default'):
     - Generate weekly ecommerce report
     - Send via WhatsApp if configured
     - Log completion

4. Update scheduler/celery_app.py beat_schedule:
   Add:
   'send-re-weekly-report': {
     'task': 'scheduler.tasks.send_real_estate_weekly_report',
     'schedule': crontab(hour=9, minute=0, day_of_week=1),
     'args': ('default',)
   },
   'send-ecommerce-weekly-report': {
     'task': 'scheduler.tasks.send_ecommerce_weekly_report',
     'schedule': crontab(hour=9, minute=30, day_of_week=1),
     'args': ('default',)
   }

Verify:
python -c "
from skills.real_estate_skills import RealEstateSkills
rs = RealEstateSkills()
priority = rs.detect_maintenance_priority('there is a gas leak in the kitchen')
assert priority == 'critical'
print('RE Skills: OK')

from skills.ecommerce_skills import EcommerceSkills
es = EcommerceSkills()
order_id = es.extract_order_id('My order #12345 has not arrived')
assert order_id == '12345'
print('Ecommerce Skills: OK')
print('Prompt 33 Industry Skills: OK')
"
```

---

## PROMPT 34 — TESTS & VERIFICATION

```
Implement Prompt 34: Phase 3 Tests & Verification

1. Create tests/test_real_estate_agent.py:

import pytest
from agents.real_estate.real_estate_agent import RealEstateAgent
from skills.real_estate_skills import RealEstateSkills

class TestRealEstateAgent:
    def test_agent_name(self):
        agent = RealEstateAgent()
        assert agent.agent_name == "GmailMind Real Estate Agent"

    def test_industry(self):
        agent = RealEstateAgent()
        assert agent.industry == "real_estate"

    def test_supported_tiers(self):
        agent = RealEstateAgent()
        assert "tier2" in agent.supported_tiers
        assert "tier1" not in agent.supported_tiers

    def test_classify_property_inquiry(self):
        agent = RealEstateAgent()
        email = {
            "subject": "Interested in your property listing",
            "body": "I would like to know more about the apartment"
        }
        assert agent.classify_email(email) == "property_inquiry"

    def test_classify_viewing_request(self):
        agent = RealEstateAgent()
        email = {
            "subject": "Schedule a viewing",
            "body": "Can I arrange a visit to see the property?"
        }
        assert agent.classify_email(email) == "viewing_request"

    def test_classify_maintenance(self):
        agent = RealEstateAgent()
        email = {
            "subject": "Maintenance Required",
            "body": "The heating is broken in my apartment"
        }
        assert agent.classify_email(email) == "maintenance_request"

    def test_classify_other(self):
        agent = RealEstateAgent()
        email = {
            "subject": "Hello",
            "body": "Just saying hi"
        }
        assert agent.classify_email(email) == "other"

class TestRealEstateSkills:
    def test_critical_maintenance(self):
        skills = RealEstateSkills()
        assert skills.detect_maintenance_priority("gas leak in kitchen") == "critical"
        assert skills.detect_maintenance_priority("flood in basement") == "critical"

    def test_high_maintenance(self):
        skills = RealEstateSkills()
        assert skills.detect_maintenance_priority("no hot water") == "high"

    def test_medium_maintenance(self):
        skills = RealEstateSkills()
        assert skills.detect_maintenance_priority("pest problem") == "medium"

2. Create tests/test_ecommerce_agent.py:

import pytest
from agents.ecommerce.ecommerce_agent import EcommerceAgent
from skills.ecommerce_skills import EcommerceSkills

class TestEcommerceAgent:
    def test_agent_name(self):
        agent = EcommerceAgent()
        assert agent.agent_name == "GmailMind E-commerce Agent"

    def test_industry(self):
        agent = EcommerceAgent()
        assert agent.industry == "ecommerce"

    def test_classify_order_inquiry(self):
        agent = EcommerceAgent()
        email = {
            "subject": "Where is my order?",
            "body": "I placed order #12345 last week and have not received it"
        }
        assert agent.classify_email(email) == "order_inquiry"

    def test_classify_refund(self):
        agent = EcommerceAgent()
        email = {
            "subject": "Refund Request",
            "body": "I want a refund for my damaged item"
        }
        assert agent.classify_email(email) == "refund_request"

    def test_classify_complaint(self):
        agent = EcommerceAgent()
        email = {
            "subject": "Complaint about service",
            "body": "I am very disappointed with my experience"
        }
        assert agent.classify_email(email) == "complaint"

    def test_classify_supplier(self):
        agent = EcommerceAgent()
        email = {
            "subject": "Invoice for bulk order",
            "body": "Please find attached our invoice for the wholesale order"
        }
        assert agent.classify_email(email) == "supplier_email"

class TestEcommerceSkills:
    def test_extract_order_id(self):
        skills = EcommerceSkills()
        assert skills.extract_order_id("My order #12345 is missing") == "12345"
        assert skills.extract_order_id("ORDER-ABC123 not delivered") is not None
        assert skills.extract_order_id("No order number here") is None

    def test_sentiment_very_negative(self):
        skills = EcommerceSkills()
        assert skills.detect_customer_sentiment("This is a scam! I will take legal action") == "very_negative"

    def test_sentiment_positive(self):
        skills = EcommerceSkills()
        assert skills.detect_customer_sentiment("I love this product, amazing quality!") == "positive"

3. Run all tests:
python -m pytest tests/ -v --tb=short

Expected results:
- All Phase 1 tests: PASS
- All Phase 2 tests: PASS
- All Phase 2.5 tests: PASS
- All Phase 3 tests: PASS
- Total: 280+ tests passing

4. Full system verification:
python -c "
print('=== GmailMind Phase 3 Verification ===')

from agents.real_estate.real_estate_agent import RealEstateAgent
re_agent = RealEstateAgent()
assert re_agent.industry == 'real_estate'
print('✅ Real Estate Agent: ACTIVE')

from agents.ecommerce.ecommerce_agent import EcommerceAgent
ec_agent = EcommerceAgent()
assert ec_agent.industry == 'ecommerce'
print('✅ E-commerce Agent: ACTIVE')

from orchestrator.orchestrator import GmailMindOrchestrator
o = GmailMindOrchestrator()
industries = o.registry.list_industries()
assert 'real_estate' in industries
assert 'ecommerce' in industries
print('✅ Orchestrator: 4 agents registered')

from skills.real_estate_skills import RealEstateSkills
from skills.ecommerce_skills import EcommerceSkills
print('✅ Industry Skills: ACTIVE')

print('')
print('Total Agents: 4 (General, HR, Real Estate, E-commerce)')
print('Status: PHASE 3 COMPLETE ✅')
print('======================================')
"

5. Git commit:
git add .
git commit -m "Phase 3 Complete - Real Estate + E-commerce Agents - 4 Industry Agents Active"
git push

PHASE 3 COMPLETE! 🎉
```

---

## PROMPT 35 — PHASE 3 COMPLETION REPORT

```
Implement Prompt 35: Phase 3 Completion Report

Create PHASE3_COMPLETION_REPORT.md in project root:

# GmailMind — Phase 3 Completion Report

## Status: COMPLETE ✅

## What Was Built

### Real Estate Agent
- Property inquiry handling with auto-reply
- Viewing scheduling with calendar integration
- Rental application processing
- Maintenance request management with priority detection
- Offer submission handling

### E-commerce Agent
- Order inquiry handling
- Refund request processing
- Customer complaint management
- Shipping inquiry handling
- Supplier email management
- Customer sentiment detection

### Database Tables Added
- properties
- property_inquiries
- property_viewings
- maintenance_requests
- order_inquiries
- refund_requests
- customer_complaints
- supplier_emails

### API Routes Added
- /real-estate/* (6 endpoints)
- /ecommerce/* (6 endpoints)

### Industry Skills
- RealEstateSkills — property listing, maintenance priority detection
- EcommerceSkills — order ID extraction, sentiment detection

## System Overview

| Phase | Status | Agents | Tests |
|-------|--------|--------|-------|
| Phase 1 | ✅ Complete | General Agent | Passing |
| Phase 2 | ✅ Complete | HR Agent + Orchestrator | Passing |
| Phase 2.5 | ✅ Complete | Enterprise Security | Passing |
| Phase 3 | ✅ Complete | Real Estate + E-commerce | Passing |

## Agent Registry
1. GeneralAgent — industry: general
2. HRAgent — industry: hr
3. RealEstateAgent — industry: real_estate
4. EcommerceAgent — industry: ecommerce

## Next Phase
Phase 4: Website + Stripe Payment + Client Dashboard

Also update CONTEXT.md with Phase 3 completion status.

Verify:
docker-compose up --build
All containers healthy ✅
All tests passing ✅

PHASE 3 COMPLETE! 🎉
Ready for Phase 4!
```

---

## QUICK REFERENCE

### Verify Each Prompt:
```bash
# Prompt 27
python -c "from agents.real_estate.real_estate_agent import RealEstateAgent; print('OK')"

# Prompt 28
python -c "from agents.ecommerce.ecommerce_agent import EcommerceAgent; print('OK')"

# Prompt 29 + 30
python scripts/setup_db.py

# Prompt 31
python -c "from orchestrator.orchestrator import GmailMindOrchestrator; o = GmailMindOrchestrator(); print(o.registry.list_industries())"

# Prompt 32
docker-compose up --build
# Open: http://localhost:8000/docs

# Prompt 33
python -c "from skills.real_estate_skills import RealEstateSkills; print('OK')"

# Prompt 34
python -m pytest tests/ -v

# Prompt 35
cat PHASE3_COMPLETION_REPORT.md
```

### Git Commit After Each Prompt:
```bash
git add .
git commit -m "Prompt 2X complete: [description]"
```

### How To Start Claude Code:
```
Please read these files completely:
1. PHASE2_PROMPTS.md
2. PHASE2.5_PROMPTS.md
3. PHASE3_PROMPTS.md

After reading confirm you understand the project structure.
Then wait for me to say which prompt to implement.
```

### After Phase 3 Complete:
```
✅ 4 Industry Agents Active
✅ Real Estate businesses can use GmailMind
✅ E-commerce businesses can use GmailMind
✅ Then start Phase 4 (Website + Stripe + Dashboard)
```
