# Prompt 32: Real Estate & E-commerce API Routes

## Overview
Created comprehensive REST API endpoints for Real Estate and E-commerce agents, providing full CRUD operations and query capabilities for their respective data models.

## Files Created

### 1. api/routes/real_estate_routes.py
Complete API for Real Estate operations with 6 endpoints.

**Router Configuration:**
- Prefix: `/real-estate`
- Tag: `Real-estate`

**Endpoints:**

#### GET /real-estate/{user_id}/inquiries
Paginated list of property inquiries.
- **Query Params:**
  - `status` (optional) - Filter by status
  - `page` (default: 1, min: 1) - Page number
  - `page_size` (default: 20, min: 1, max: 100) - Items per page
- **Response:**
  ```json
  {
    "success": true,
    "data": {
      "inquiries": [...],
      "page": 1,
      "page_size": 20,
      "total": 45
    }
  }
  ```

#### GET /real-estate/{user_id}/viewings
List of upcoming property viewings.
- **Query Params:**
  - `days_ahead` (default: 7, min: 1, max: 90) - Number of days to look ahead
- **Response:**
  ```json
  {
    "success": true,
    "data": {
      "viewings": [
        {
          "id": 1,
          "client_email": "client@example.com",
          "property_address": "123 Main St",
          "viewing_date": "2026-03-15T10:00:00",
          "status": "scheduled"
        }
      ],
      "days_ahead": 7
    }
  }
  ```

#### GET /real-estate/{user_id}/maintenance
List of maintenance requests.
- **Query Params:**
  - `status` (default: "open") - Filter by status
- **Response:** List of maintenance requests ordered by priority

#### GET /real-estate/{user_id}/properties
List of active property listings.
- **Response:** All available properties with full details

#### POST /real-estate/{user_id}/properties
Create a new property listing.
- **Body:**
  ```json
  {
    "address": "123 Main St",
    "property_type": "residential",
    "price": 450000,
    "bedrooms": 3,
    "bathrooms": 2,
    "size_sqft": 2000,
    "location": "Downtown",
    "listing_type": "sale"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "data": {
      "property_id": 42
    }
  }
  ```

#### GET /real-estate/{user_id}/summary
Get summary statistics.
- **Response:**
  ```json
  {
    "success": true,
    "data": {
      "total_inquiries": 25,
      "viewings_scheduled": 8,
      "open_maintenance": 3,
      "properties_listed": 12
    }
  }
  ```

---

### 2. api/routes/ecommerce_routes.py
Complete API for E-commerce operations with 6 endpoints.

**Router Configuration:**
- Prefix: `/ecommerce`
- Tag: `Ecommerce`

**Endpoints:**

#### GET /ecommerce/{user_id}/inquiries
Paginated list of order inquiries.
- **Query Params:**
  - `inquiry_type` (optional) - Filter by type (e.g., "status", "tracking")
  - `page` (default: 1)
  - `page_size` (default: 20, max: 100)
- **Response:** Paginated inquiry list

#### GET /ecommerce/{user_id}/refunds
List of refund requests.
- **Query Params:**
  - `status` (default: "pending") - pending, approved, processed, rejected
- **Response:**
  ```json
  {
    "success": true,
    "data": {
      "refunds": [
        {
          "id": 1,
          "customer_email": "customer@example.com",
          "order_id": "ORDER-12345",
          "reason": "Product defective",
          "amount": 99.99,
          "status": "pending",
          "created_at": "2026-03-10T14:30:00"
        }
      ],
      "status": "pending"
    }
  }
  ```

#### PUT /ecommerce/{user_id}/refunds/{refund_id}
Update refund status.
- **Body:**
  ```json
  {
    "status": "approved"
  }
  ```
- **Valid Statuses:** pending, approved, processed, rejected
- **Response:**
  ```json
  {
    "success": true,
    "data": {
      "refund_id": 1,
      "new_status": "approved"
    }
  }
  ```

#### GET /ecommerce/{user_id}/complaints
List of customer complaints.
- **Query Params:**
  - `priority` (optional) - low, medium, high, critical
  - `status` (optional) - open, investigating, resolved, closed
- **Response:** Filtered complaint list ordered by priority and date

#### PUT /ecommerce/{user_id}/complaints/{complaint_id}
Update complaint status and resolution.
- **Body:**
  ```json
  {
    "status": "resolved",
    "resolution": "Issued full refund and sent replacement product"
  }
  ```
- **Valid Statuses:** open, investigating, resolved, closed
- **Response:**
  ```json
  {
    "success": true,
    "data": {}
  }
  ```

#### GET /ecommerce/{user_id}/summary
Get summary statistics.
- **Response:**
  ```json
  {
    "success": true,
    "data": {
      "total_inquiries": 142,
      "pending_refunds": 8,
      "open_complaints": 3,
      "resolved_today": 5
    }
  }
  ```

---

### 3. api/main.py
Updated to register both new routers.

**Added Imports:**
```python
from api.routes.real_estate_routes import router as real_estate_router
from api.routes.ecommerce_routes import router as ecommerce_router
```

**Added Registrations:**
```python
app.include_router(real_estate_router)  # Prefix /real-estate
app.include_router(ecommerce_router)    # Prefix /ecommerce
```

---

## Features

### Pagination
Both inquiry endpoints support pagination:
- Default: 20 items per page
- Configurable via `page` and `page_size` query parameters
- Response includes total count for UI pagination

### Filtering
Smart filtering on all list endpoints:
- Real Estate inquiries: by status
- Real Estate maintenance: by status (default: "open")
- E-commerce inquiries: by inquiry_type
- E-commerce refunds: by status (default: "pending")
- E-commerce complaints: by priority AND status

### Error Handling
Consistent error responses:
```json
{
  "success": false,
  "data": null,
  "error": "Descriptive error message"
}
```

### Validation
- Status validation on PUT operations
- Required field checking (e.g., address for properties)
- Query parameter constraints (min/max values)

### Database Operations
- Read operations use optimized SELECT queries
- Write operations use parameterized queries (SQL injection safe)
- Proper transaction handling with rollback on errors
- Connection cleanup in finally blocks

---

## API Documentation

Once the server is running, visit:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

New sections will appear:
- **Real-estate** - 6 endpoints
- **Ecommerce** - 6 endpoints

---

## Usage Examples

### Real Estate: Get Today's Viewings
```bash
GET /real-estate/user123/viewings?days_ahead=1
```

### Real Estate: Create Property
```bash
POST /real-estate/user123/properties
{
  "address": "456 Oak Ave",
  "property_type": "residential",
  "price": 550000,
  "bedrooms": 4,
  "bathrooms": 3,
  "size_sqft": 2500,
  "location": "Suburbs",
  "listing_type": "sale"
}
```

### E-commerce: Approve Refund
```bash
PUT /ecommerce/user456/refunds/42
{
  "status": "approved"
}
```

### E-commerce: Get High-Priority Complaints
```bash
GET /ecommerce/user456/complaints?priority=high&status=open
```

---

## Status
✅ **Implementation Complete** - Prompt 32
- 2 new route files created (12 endpoints total)
- Both routers registered in FastAPI app
- Full CRUD operations for both domains
- Pagination, filtering, and validation
- Consistent error handling
- Ready for Swagger/ReDoc documentation
