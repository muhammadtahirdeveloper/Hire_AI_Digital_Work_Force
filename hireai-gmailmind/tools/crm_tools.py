"""CRM tools for the GmailMind agent.

Provides two operations:
  1. get_crm_contact  — Look up a contact by email (HubSpot or local DB)
  2. update_crm       — Update a contact record (HubSpot or local DB)

Integration priority:
  - If HUBSPOT_API_KEY is configured → use HubSpot API.
  - Otherwise → fall back to local PostgreSQL sender_profiles table.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from config.database import SessionLocal
from config.settings import HUBSPOT_API_KEY, HUBSPOT_BASE_URL
from memory.long_term import get_sender_memory, update_sender_memory
from memory.schemas import SenderProfileUpdate
from models.tool_models import ContactProfile, CrmUpdateResponse

logger = logging.getLogger(__name__)


def _hubspot_configured() -> bool:
    """Return True if HubSpot API credentials are present."""
    return bool(HUBSPOT_API_KEY)


# ===========================================================================
# 1. get_crm_contact
# ===========================================================================


def get_crm_contact(email: str) -> Optional[ContactProfile]:
    """Look up a contact by email address.

    Checks HubSpot first (if configured), otherwise falls back to the
    local PostgreSQL sender_profiles table.

    Args:
        email: The contact's email address.

    Returns:
        A ContactProfile if found, otherwise None.
    """
    logger.info("get_crm_contact: Looking up %s", email)

    if _hubspot_configured():
        return _get_hubspot_contact(email)

    return _get_local_contact(email)


def _get_hubspot_contact(email: str) -> Optional[ContactProfile]:
    """Fetch a contact from HubSpot CRM by email.

    Args:
        email: Contact email address.

    Returns:
        A ContactProfile sourced from HubSpot, or None.
    """
    logger.info("_get_hubspot_contact: Querying HubSpot for %s", email)

    try:
        url = f"{HUBSPOT_BASE_URL}/crm/v3/objects/contacts/search"
        headers = {
            "Authorization": f"Bearer {HUBSPOT_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": email,
                        }
                    ]
                }
            ],
            "properties": [
                "email",
                "firstname",
                "lastname",
                "company",
                "phone",
                "jobtitle",
                "lifecyclestage",
                "hs_last_activity_date",
            ],
        }

        with httpx.Client(timeout=15) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()

        data = resp.json()
        results = data.get("results", [])

        if not results:
            logger.info("_get_hubspot_contact: No HubSpot contact for %s.", email)
            return None

        props = results[0].get("properties", {})
        first = props.get("firstname", "") or ""
        last = props.get("lastname", "") or ""
        full_name = f"{first} {last}".strip() or None

        last_activity_raw = props.get("hs_last_activity_date")
        last_activity = None
        if last_activity_raw:
            try:
                last_activity = datetime.fromisoformat(
                    last_activity_raw.replace("Z", "+00:00")
                )
            except (ValueError, TypeError):
                pass

        contact = ContactProfile(
            email=email,
            name=full_name,
            company=props.get("company"),
            phone=props.get("phone"),
            job_title=props.get("jobtitle"),
            lifecycle_stage=props.get("lifecyclestage"),
            last_activity=last_activity,
            source="hubspot",
            properties=props,
        )

        logger.info("_get_hubspot_contact: Found HubSpot contact for %s.", email)
        return contact

    except httpx.HTTPStatusError as exc:
        logger.error(
            "_get_hubspot_contact: HubSpot API error %d — %s",
            exc.response.status_code,
            exc.response.text,
        )
        return None
    except Exception as exc:
        logger.error("_get_hubspot_contact: Unexpected error — %s", exc)
        return None


def _get_local_contact(email: str) -> Optional[ContactProfile]:
    """Fetch a contact from the local sender_profiles table.

    Args:
        email: Contact email address.

    Returns:
        A ContactProfile sourced from local DB, or None.
    """
    logger.info("_get_local_contact: Querying local DB for %s", email)

    profile = get_sender_memory(email)
    if profile is None:
        logger.info("_get_local_contact: No local profile for %s.", email)
        return None

    contact = ContactProfile(
        email=profile.email,
        name=profile.name,
        company=profile.company,
        last_activity=profile.last_interaction,
        tags=profile.tags,
        source="local",
    )

    logger.info("_get_local_contact: Found local contact for %s.", email)
    return contact


# ===========================================================================
# 2. update_crm
# ===========================================================================


def update_crm(email: str, action: str, data: dict) -> CrmUpdateResponse:
    """Update a CRM contact record.

    Routes to HubSpot if configured, otherwise updates the local
    PostgreSQL sender_profiles table.

    Args:
        email: Contact email address.
        action: Description of the action (e.g. 'note_added', 'tag_updated',
                'lifecycle_changed').
        data: Key-value pairs to update. Supported keys vary by backend:
              - HubSpot: any HubSpot contact property name
              - Local: 'name', 'company', 'tags', 'history_entry'

    Returns:
        A CrmUpdateResponse indicating success or failure with reason.
    """
    logger.info("update_crm: email=%s, action=%s, data_keys=%s", email, action, list(data.keys()))

    if _hubspot_configured():
        return _update_hubspot_contact(email, action, data)

    return _update_local_contact(email, action, data)


def _update_hubspot_contact(email: str, action: str, data: dict) -> CrmUpdateResponse:
    """Push an update to HubSpot CRM.

    Args:
        email: Contact email.
        action: Action label for logging.
        data: Properties to update on the HubSpot contact.

    Returns:
        CrmUpdateResponse.
    """
    logger.info("_update_hubspot_contact: Updating HubSpot for %s — %s", email, action)

    try:
        # First, find the contact ID
        search_url = f"{HUBSPOT_BASE_URL}/crm/v3/objects/contacts/search"
        headers = {
            "Authorization": f"Bearer {HUBSPOT_API_KEY}",
            "Content-Type": "application/json",
        }
        search_payload = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "email",
                            "operator": "EQ",
                            "value": email,
                        }
                    ]
                }
            ],
        }

        with httpx.Client(timeout=15) as client:
            search_resp = client.post(search_url, json=search_payload, headers=headers)
            search_resp.raise_for_status()

        results = search_resp.json().get("results", [])

        if not results:
            logger.warning(
                "_update_hubspot_contact: Contact %s not found in HubSpot. "
                "Falling back to local DB.",
                email,
            )
            return _update_local_contact(email, action, data)

        contact_id = results[0]["id"]

        # Now patch the contact
        update_url = f"{HUBSPOT_BASE_URL}/crm/v3/objects/contacts/{contact_id}"

        with httpx.Client(timeout=15) as client:
            update_resp = client.patch(
                update_url,
                json={"properties": data},
                headers=headers,
            )
            update_resp.raise_for_status()

        logger.info(
            "_update_hubspot_contact: Updated HubSpot contact %s (id=%s).",
            email,
            contact_id,
        )

        return CrmUpdateResponse(
            success=True,
            source="hubspot",
            action=action,
        )

    except httpx.HTTPStatusError as exc:
        reason = f"HubSpot API error {exc.response.status_code}: {exc.response.text}"
        logger.error("_update_hubspot_contact: %s", reason)
        return CrmUpdateResponse(success=False, source="hubspot", action=action, reason=reason)
    except Exception as exc:
        reason = f"Unexpected error: {exc}"
        logger.error("_update_hubspot_contact: %s", reason)
        return CrmUpdateResponse(success=False, source="hubspot", action=action, reason=reason)


def _update_local_contact(email: str, action: str, data: dict) -> CrmUpdateResponse:
    """Update the local PostgreSQL sender_profiles table.

    Args:
        email: Contact email.
        action: Action label for the history entry.
        data: Fields to update — supports 'name', 'company', 'tags'.

    Returns:
        CrmUpdateResponse.
    """
    logger.info("_update_local_contact: Updating local DB for %s — %s", email, action)

    try:
        update = SenderProfileUpdate(
            name=data.get("name"),
            company=data.get("company"),
            tags=data.get("tags"),
            history_entry={
                "action": action,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )

        update_sender_memory(email, update)

        logger.info("_update_local_contact: Updated local profile for %s.", email)

        return CrmUpdateResponse(
            success=True,
            source="local",
            action=action,
        )

    except Exception as exc:
        reason = f"Local DB error: {exc}"
        logger.error("_update_local_contact: %s", reason)
        return CrmUpdateResponse(success=False, source="local", action=action, reason=reason)
