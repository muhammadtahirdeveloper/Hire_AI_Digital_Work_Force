"""Email templates for E-commerce Agent."""

ECOMMERCE_TEMPLATES = {
    'order_confirmation': """Dear {customer_name},

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
""",

    'refund_initiated': """Dear {customer_name},

We have initiated your refund for Order #{order_id}.

Refund Amount: {refund_amount}
Reason: {reason}
Processing Time: 3-5 business days

The amount will be credited to your original payment method.
If you have any questions, please don't hesitate to contact us.

Best regards,
{company_name} Support Team
""",

    'complaint_acknowledged': """Dear {customer_name},

Thank you for bringing this to our attention.

We have received your complaint regarding: {complaint_description}
Reference Number: {reference_id}

Our team is investigating this matter and will respond within 24 hours.
We sincerely apologize for any inconvenience caused.

Best regards,
{company_name} Support Team
""",

    'shipping_update': """Dear {customer_name},

Your order #{order_id} has been {shipping_status}.

Tracking Number: {tracking_number}
Estimated Delivery: {delivery_date}
Carrier: {carrier}

You can track your package at: {tracking_url}

Best regards,
{company_name} Team
""",

    'supplier_acknowledgment': """Dear {supplier_name},

Thank you for your message regarding {subject}.

We have noted your update and will process it accordingly.
Our team will be in touch within 1-2 business days.

Best regards,
{company_name} Procurement Team
""",

    'review_request': """Dear {customer_name},

We hope you are enjoying your recent purchase from {company_name}!

We would love to hear your feedback.
Please take a moment to leave a review — it helps us improve
and helps other customers make informed decisions.

Thank you for your support!

Best regards,
{company_name} Team
""",
}
