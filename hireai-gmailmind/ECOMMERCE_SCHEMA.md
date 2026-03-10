# E-commerce Database Schema (Prompt 30)

## Overview
Four tables for managing customer orders, refunds, complaints, and supplier communications in online businesses.

## Tables Created

### 1. order_inquiries
Tracks customer inquiries about orders.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique inquiry ID |
| user_id | VARCHAR(255) | NOT NULL | Business owner user ID |
| customer_email | VARCHAR(320) | NOT NULL | Customer's email |
| order_id | VARCHAR(100) | | Order being inquired about |
| inquiry_type | VARCHAR(50) | DEFAULT 'general' | Type (status, tracking, general) |
| status | VARCHAR(50) | DEFAULT 'open' | open, responded, closed |
| notes | TEXT | | Additional notes |
| created_at | TIMESTAMP | DEFAULT NOW() | Created timestamp |

**Index**: `idx_order_inquiries_user` ON user_id

---

### 2. refund_requests
Tracks customer refund requests and processing.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique refund ID |
| user_id | VARCHAR(255) | NOT NULL | Business owner user ID |
| customer_email | VARCHAR(320) | NOT NULL | Customer's email |
| order_id | VARCHAR(100) | | Order to be refunded |
| reason | TEXT | | Reason for refund |
| amount | DECIMAL(10,2) | | Refund amount |
| status | VARCHAR(50) | DEFAULT 'pending' | pending, approved, processed, rejected |
| created_at | TIMESTAMP | DEFAULT NOW() | Created timestamp |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last updated |

**Index**: `idx_refund_requests_user` ON user_id

---

### 3. customer_complaints
Tracks and manages customer complaints.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique complaint ID |
| user_id | VARCHAR(255) | NOT NULL | Business owner user ID |
| customer_email | VARCHAR(320) | NOT NULL | Customer's email |
| description | TEXT | | Complaint description |
| priority | VARCHAR(20) | DEFAULT 'medium' | low, medium, high, critical |
| status | VARCHAR(50) | DEFAULT 'open' | open, investigating, resolved, closed |
| resolution | TEXT | | How the complaint was resolved |
| created_at | TIMESTAMP | DEFAULT NOW() | Created timestamp |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last updated |

**Index**: `idx_complaints_user` ON user_id

---

### 4. supplier_emails
Tracks communications with suppliers.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique email ID |
| user_id | VARCHAR(255) | NOT NULL | Business owner user ID |
| supplier_email | VARCHAR(320) | NOT NULL | Supplier's email |
| subject | VARCHAR(500) | | Email subject |
| email_type | VARCHAR(50) | DEFAULT 'general' | invoice, stock, payment, general |
| status | VARCHAR(50) | DEFAULT 'received' | received, reviewed, actioned |
| notes | TEXT | | Additional notes |
| created_at | TIMESTAMP | DEFAULT NOW() | Created timestamp |

**Index**: `idx_supplier_emails_user` ON user_id

---

## Usage

### Setup Database
```bash
python scripts/setup_db.py
```

This will create all E-commerce tables along with existing HR, Real Estate, and security tables.

### Agent Integration
The EcommerceAgent (Prompt 28) uses these tables via the OrderTracker class:
- `order_tracker.log_order_inquiry()` → inserts into order_inquiries
- `order_tracker.log_refund_request()` → inserts into refund_requests
- `order_tracker.log_complaint()` → inserts into customer_complaints
- `order_tracker.get_support_summary()` → aggregates support metrics

---

## Common Queries

### Get pending refunds for a user
```sql
SELECT * FROM refund_requests
WHERE user_id = 'user123'
  AND status = 'pending'
ORDER BY created_at DESC;
```

### Get high-priority complaints
```sql
SELECT * FROM customer_complaints
WHERE user_id = 'user123'
  AND priority IN ('high', 'critical')
  AND status = 'open'
ORDER BY created_at ASC;
```

### Get today's order inquiries
```sql
SELECT * FROM order_inquiries
WHERE user_id = 'user123'
  AND created_at::date = CURRENT_DATE
ORDER BY created_at DESC;
```

### Get unreviewed supplier emails
```sql
SELECT * FROM supplier_emails
WHERE user_id = 'user123'
  AND status = 'received'
ORDER BY created_at DESC;
```

---

## Status
✅ **Implementation Complete** - Prompt 30
- All tables match specification
- Indexes created for performance
- Integrated into setup_db.py main() function
- Ready for deployment
