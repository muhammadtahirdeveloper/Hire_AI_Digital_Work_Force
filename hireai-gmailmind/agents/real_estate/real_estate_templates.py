"""Email templates for Real Estate Agent."""

REAL_ESTATE_TEMPLATES = {
    'property_inquiry_reply': """Dear {client_name},

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
""",

    'viewing_confirmation': """Dear {client_name},

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
""",

    'rental_application_received': """Dear {applicant_name},

Thank you for submitting your rental application for {property_address}.

We have received your application and will review it within 2-3 business days.
We will contact you shortly with an update.

Best regards,
{agent_name}
{company_name}
""",

    'maintenance_request_received': """Dear {tenant_name},

We have received your maintenance request regarding: {issue_description}

Property: {property_address}
Request ID: {request_id}
Priority: {priority}

Our team will be in touch within {response_time} to schedule the repair.

Best regards,
{company_name} Property Management
""",

    'offer_received': """Dear {seller_name},

We have received an offer on your property at {property_address}:

Offered Price: {offer_price}
Offered By: {buyer_name}
Offer Valid Until: {valid_until}

Please review and let us know if you would like to accept, counter, or decline.

Best regards,
{agent_name}
{company_name}
""",

    'lease_renewal_reminder': """Dear {tenant_name},

This is a friendly reminder that your lease for {property_address}
is due to expire on {expiry_date}.

We would love to have you continue as our tenant.
Please let us know if you would like to renew your lease.

Current Rent: {current_rent}
Proposed New Rent: {new_rent}

Please respond by {response_deadline} to secure your tenancy.

Best regards,
{company_name} Property Management
""",
}
