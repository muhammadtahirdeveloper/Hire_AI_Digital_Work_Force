# Prompt 31: Orchestrator & User Router Updates

## Overview
Updated the orchestrator system to support all 4 specialist agents with proper industry routing, feature gating, and API validation.

## Changes Made

### 1. orchestrator/user_router.py

**Added VALID_INDUSTRIES constant:**
```python
VALID_INDUSTRIES = ['general', 'hr', 'real_estate', 'ecommerce']
```

**Enhanced get_user_industry() method:**
- Validates industry against VALID_INDUSTRIES list
- Logs warning if invalid industry is found
- Automatically defaults to 'general' for invalid industries
- Example warning: "Invalid industry 'xyz' for user=user123. Valid options: [...]. Defaulting to 'general'."

### 2. orchestrator/feature_gates.py

**Updated Tier 2 Features:**
Added industry-specific features:
- `property_tracker` - Real Estate agent feature
- `viewing_scheduler` - Real Estate agent feature
- `order_tracker` - E-commerce agent feature
- `refund_manager` - E-commerce agent feature

**Updated Tier 3 Features:**
Added advanced features:
- `crm_sync` - Advanced CRM synchronization
- `advanced_analytics` - Advanced reporting and analytics
- `bulk_email` - Bulk email operations

### 3. orchestrator/orchestrator.py

**Agent Registration:**
All 4 agents are properly registered in `_register_default_agents()`:
- ✅ GeneralAgent → 'general'
- ✅ HRAgent → 'hr'
- ✅ RealEstateAgent → 'real_estate'
- ✅ EcommerceAgent → 'ecommerce'

Each registration includes graceful error handling with informative log messages.

### 4. api/routes/orchestrator_routes.py

**New Endpoint: GET /platform/agents**
```json
{
  "success": true,
  "data": {
    "registered_agents": ["general", "hr", "real_estate", "ecommerce"],
    "total": 4
  }
}
```

**Updated Endpoint: POST /platform/users/{user_id}/setup**
- Added industry validation against VALID_INDUSTRIES
- Returns 400 error if invalid industry is provided
- Error message: "Invalid industry 'xyz'. Must be one of: ['general', 'hr', 'real_estate', 'ecommerce']"

**Updated Endpoint: GET /platform/stats**
- Now includes per-agent user counts for all 4 industries:
```json
{
  "agents_running": {
    "general": 5,
    "hr": 3,
    "real_estate": 2,
    "ecommerce": 1
  }
}
```

## API Examples

### List All Registered Agents
```bash
GET /platform/agents

Response:
{
  "success": true,
  "data": {
    "registered_agents": ["general", "hr", "real_estate", "ecommerce"],
    "total": 4
  }
}
```

### Setup User with Industry Validation
```bash
POST /platform/users/user123/setup
{
  "industry": "real_estate",
  "tier": "tier2"
}

Success Response:
{
  "success": true,
  "data": {
    "user_id": "user123",
    "industry": "real_estate",
    "tier": "tier2"
  }
}

Error Response (invalid industry):
{
  "success": false,
  "error": "Invalid industry 'xyz'. Must be one of: ['general', 'hr', 'real_estate', 'ecommerce']"
}
```

## Feature Gate Usage

### Check if user can use Real Estate features
```python
from orchestrator.feature_gates import FeatureGate

gates = FeatureGate()

# Tier 2 user can use property_tracker
can_track = gates.can_use_feature("user123", "property_tracker")  # True for tier2+

# Tier 1 user cannot use property_tracker
can_track = gates.can_use_feature("tier1_user", "property_tracker")  # False
```

### Check if user can use E-commerce features
```python
# Tier 2 user can use order_tracker and refund_manager
can_track = gates.can_use_feature("user456", "order_tracker")  # True for tier2+
can_refund = gates.can_use_feature("user456", "refund_manager")  # True for tier2+
```

## Verification

All changes verified:
- ✅ VALID_INDUSTRIES list contains all 4 industries
- ✅ Industry validation logic present in UserRouter
- ✅ Warning logs for invalid industries
- ✅ All 4 agents registered in orchestrator
- ✅ Tier 2 features include real_estate and ecommerce features
- ✅ Tier 3 features include advanced capabilities
- ✅ API endpoint GET /platform/agents added
- ✅ API endpoint POST /platform/users/{user_id}/setup validates industry
- ✅ API endpoint GET /platform/stats includes all 4 industries

## Impact

**Backward Compatibility:**
- ✅ Existing 'general' and 'hr' industries continue to work
- ✅ Invalid industries automatically default to 'general' with warning
- ✅ No breaking changes to existing API contracts

**New Capabilities:**
- 🎯 Users can now be assigned to 'real_estate' or 'ecommerce' industries
- 🎯 Real Estate and E-commerce agents fully integrated
- 🎯 Feature gates properly restrict access by tier
- 🎯 API provides full visibility into registered agents

## Status
✅ **Implementation Complete** - Prompt 31
- All 4 agents fully integrated into orchestrator
- Industry routing with validation
- Feature gating for new agent capabilities
- API endpoints updated and validated
