# Real Estate Database Schema (Prompt 29)

## Overview
Four tables for managing property listings, client inquiries, viewings, and maintenance requests.

## Tables Created

### 1. properties
Stores property listings managed by the user.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique property ID |
| user_id | VARCHAR(255) | NOT NULL | Owner/agent user ID |
| address | VARCHAR(500) | NOT NULL | Property address |
| property_type | VARCHAR(50) | DEFAULT 'residential' | Type (residential, commercial, etc.) |
| status | VARCHAR(50) | DEFAULT 'available' | Availability status |
| price | DECIMAL(12,2) | | Listing price |
| bedrooms | INTEGER | DEFAULT 0 | Number of bedrooms |
| bathrooms | INTEGER | DEFAULT 0 | Number of bathrooms |
| size_sqft | INTEGER | DEFAULT 0 | Property size in sq ft |
| location | VARCHAR(255) | | Location/neighborhood |
| description | TEXT | | Property description |
| listing_type | VARCHAR(20) | DEFAULT 'sale' | sale or rental |
| created_at | TIMESTAMP | DEFAULT NOW() | Created timestamp |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last updated |

**Index**: `idx_properties_user_id` ON user_id

---

### 2. property_inquiries
Tracks client inquiries about properties.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique inquiry ID |
| user_id | VARCHAR(255) | NOT NULL | Agent user ID |
| client_email | VARCHAR(320) | NOT NULL | Client's email |
| property_address | VARCHAR(500) | | Property inquired about |
| inquiry_type | VARCHAR(50) | DEFAULT 'general' | Type of inquiry |
| status | VARCHAR(50) | DEFAULT 'new' | new, contacted, closed |
| notes | TEXT | | Additional notes |
| created_at | TIMESTAMP | DEFAULT NOW() | Created timestamp |

**Index**: `idx_property_inquiries_user` ON user_id

---

### 3. property_viewings
Schedules and tracks property viewings.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique viewing ID |
| user_id | VARCHAR(255) | NOT NULL | Agent user ID |
| client_email | VARCHAR(320) | NOT NULL | Client's email |
| property_address | VARCHAR(500) | | Property to view |
| viewing_date | TIMESTAMP | | Scheduled date/time |
| status | VARCHAR(50) | DEFAULT 'scheduled' | scheduled, completed, cancelled |
| notes | TEXT | | Additional notes |
| created_at | TIMESTAMP | DEFAULT NOW() | Created timestamp |

**Index**: `idx_property_viewings_user` ON user_id

---

### 4. maintenance_requests
Tracks tenant maintenance requests.

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| id | SERIAL | PRIMARY KEY | Unique request ID |
| user_id | VARCHAR(255) | NOT NULL | Landlord/agent user ID |
| tenant_email | VARCHAR(320) | NOT NULL | Tenant's email |
| property_address | VARCHAR(500) | | Property requiring maintenance |
| issue_description | TEXT | | Description of issue |
| priority | VARCHAR(20) | DEFAULT 'medium' | low, medium, high, critical |
| status | VARCHAR(50) | DEFAULT 'open' | open, in_progress, resolved |
| created_at | TIMESTAMP | DEFAULT NOW() | Created timestamp |
| updated_at | TIMESTAMP | DEFAULT NOW() | Last updated |

**Index**: `idx_maintenance_user` ON user_id

---

## Usage

### Setup Database
```bash
python scripts/setup_db.py
```

This will create all Real Estate tables along with the existing HR and security tables.

### Agent Integration
The RealEstateAgent (Prompt 27) uses these tables via the PropertyTracker class:
- `property_tracker.log_inquiry()` → inserts into property_inquiries
- `property_tracker.log_viewing()` → inserts into property_viewings
- `property_tracker.get_property()` → queries properties table
- `property_tracker.get_inquiry_summary()` → aggregates inquiry data

---

## Status
✅ **Implementation Complete** - Prompt 29
- All tables match specification
- Indexes created for performance
- Integrated into setup_db.py main() function
- Ready for deployment
