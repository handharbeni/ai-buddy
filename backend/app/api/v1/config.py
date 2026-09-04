"""Public configuration endpoint — exposes branding to frontend."""

from fastapi import APIRouter

from app.config import get_branding

router = APIRouter(tags=["config"])


@router.get("/config")
async def get_public_config():
    """Public configuration exposed to the frontend.

    Frontend uses this to display project name, tagline, etc.
    Override via env vars: APP_NAME, APP_TAGLINE, APP_INSTITUTION, APP_DOMAIN.
    """
    branding = get_branding()
    return {
        "app_name": branding.name,
        "app_short_name": branding.short_name,
        "tagline": branding.tagline,
        "institution": branding.institution,
        "domain": branding.domain,
        "version": branding.version,
    }
