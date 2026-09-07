"""
Context processor for Provider status.

Makes provider status available in all templates so navigation can
show/hide Provider Dashboard link based on the user's approval state.
"""
from .models import ProviderProfile


def provider_context(request):
    """
    Adds to every template context:
      - user_provider_profile: ProviderProfile or None
      - is_approved_provider: bool
      - is_pending_provider: bool
    """
    if not request.user.is_authenticated:
        return {
            "user_provider_profile": None,
            "is_approved_provider": False,
            "is_pending_provider": False,
        }

    try:
        profile = request.user.provider_profile
    except ProviderProfile.DoesNotExist:
        profile = None

    return {
        "user_provider_profile": profile,
        "is_approved_provider": profile is not None and profile.is_approved,
        "is_pending_provider": profile is not None and profile.is_pending,
    }
