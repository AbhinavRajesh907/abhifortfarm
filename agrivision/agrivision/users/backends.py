from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q

User = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):
    """
    Authenticates against settings.AUTH_USER_MODEL using either username or email.
    Supports credentials passed as 'username' or 'email'.
    """

    def authenticate(self, request, username=None, password=None, email=None, **kwargs):
        login_identifier = username or email or kwargs.get(User.USERNAME_FIELD)
        if not login_identifier or not password:
            return None

        try:
            user = User.objects.filter(
                Q(username__iexact=login_identifier) | Q(email__iexact=login_identifier)
            ).first()
        except Exception:
            return None

        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
