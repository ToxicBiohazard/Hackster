"""Helpers for minor flagging and parental consent verification."""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone

import aiohttp
from discord import Forbidden, Guild, HTTPException, Member
from sqlalchemy import select

from src.core import settings
from src.database.models import HtbDiscordLink, MinorReport, MinorReviewReviewer
from src.database.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

# Cache for reviewer IDs (TTL 60s) to avoid DB hit on every button interaction.
_reviewer_ids_cache: tuple[int, ...] | None = None
_reviewer_ids_cache_ts: float = 0
REVIEWER_CACHE_TTL_SEC = 60

PENDING = "pending"
APPROVED = "approved"
DENIED = "denied"
CONSENT_VERIFIED = "consent_verified"


async def check_parental_consent(account_identifier: str) -> bool:
    """
    Check if parental consent form exists via Cloud Function.

    POST to PARENTAL_CONSENT_CHECK_URL with file_name set to the user's SSO UUID.
    Returns True if consent exists (e.g. 200), False otherwise (404, timeout, error).
    """
    if not account_identifier:
        return False
    url = getattr(settings, "PARENTAL_CONSENT_CHECK_URL", None) or ""
    if not url:
        logger.warning("PARENTAL_CONSENT_CHECK_URL not set; consent check skipped.")
        return False
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={"file_name": account_identifier},
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                return resp.status == 200
    except aiohttp.ClientError as e:
        logger.warning("Parental consent check request failed: %s", e)
        return False
    except asyncio.TimeoutError as e:
        logger.warning("Parental consent check timed out: %s", e)
        return False


async def assign_minor_role(member: Member, guild: Guild) -> bool:
    """Assign the discrete minor role to the member. Returns True if added."""
    role_id = settings.roles.VERIFIED_MINOR
    role = guild.get_role(role_id)
    if not role:
        return False
    if role in member.roles:
        return False
    try:
        await member.add_roles(role, atomic=True)
        return True
    except (Forbidden, HTTPException) as e:
        logger.warning("Failed to assign minor role to %s: %s", member.id, e)
        return False


async def get_account_identifier_for_discord(discord_user_id: int) -> str | None:
    """Get HTB account identifier (SSO UUID) for a Discord user from HtbDiscordLink."""
    async with AsyncSessionLocal() as session:
        stmt = select(HtbDiscordLink).filter(
            HtbDiscordLink.discord_user_id == discord_user_id
        ).limit(1)
        result = await session.scalars(stmt)
        link = result.first()
        if link:
            return link.account_identifier
        return None


async def get_htb_user_id_for_discord(discord_user_id: int) -> int | None:
    """Get HTB user ID for a Discord user from HtbDiscordLink."""
    async with AsyncSessionLocal() as session:
        stmt = select(HtbDiscordLink).filter(
            HtbDiscordLink.discord_user_id == discord_user_id
        ).limit(1)
        result = await session.scalars(stmt)
        link = result.first()
        if link:
            return int(link.htb_user_id)
        return None


async def get_active_minor_report(user_id: int) -> MinorReport | None:
    """Get an active (pending) minor report for the user, if any."""
    async with AsyncSessionLocal() as session:
        stmt = (
            select(MinorReport)
            .filter(MinorReport.user_id == user_id, MinorReport.status == PENDING)
            .limit(1)
        )
        result = await session.scalars(stmt)
        return result.first()


def calculate_ban_duration(suspected_age: int) -> int:
    """
    Return Unix epoch timestamp when ban should end (user turns 18).

    suspected_age must be 1-17. Ban duration is (18 - suspected_age) years from now.
    """
    if suspected_age < 1 or suspected_age > 17:
        raise ValueError("suspected_age must be between 1 and 17")
    now = datetime.now(timezone.utc)
    years_until_18 = 18 - suspected_age
    end = now + timedelta(days=365 * years_until_18)
    return int(end.timestamp())


def years_until_18(suspected_age: int) -> int:
    """Return number of years until user turns 18."""
    if suspected_age < 1 or suspected_age > 17:
        raise ValueError("suspected_age must be between 1 and 17")
    return 18 - suspected_age


async def get_minor_review_reviewer_ids() -> tuple[int, ...]:
    """Return Discord user IDs of users allowed to review minor reports (from DB)."""
    global _reviewer_ids_cache, _reviewer_ids_cache_ts
    now = time.monotonic()
    if _reviewer_ids_cache is not None and (now - _reviewer_ids_cache_ts) < REVIEWER_CACHE_TTL_SEC:
        return _reviewer_ids_cache
    async with AsyncSessionLocal() as session:
        stmt = select(MinorReviewReviewer.user_id)
        result = await session.scalars(stmt)
        _reviewer_ids_cache = tuple(int(uid) for uid in result.all())
        _reviewer_ids_cache_ts = now
        return _reviewer_ids_cache


async def is_minor_review_moderator(user_id: int) -> bool:
    """Return True if the user is allowed to review minor reports (from DB)."""
    reviewer_ids = await get_minor_review_reviewer_ids()
    return user_id in reviewer_ids


def invalidate_reviewer_ids_cache() -> None:
    """Clear the reviewer IDs cache so the next check reads from the DB."""
    global _reviewer_ids_cache
    _reviewer_ids_cache = None
