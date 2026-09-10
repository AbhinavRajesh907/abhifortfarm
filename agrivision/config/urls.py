from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include
from django.urls import path
from django.views import defaults as default_views
from django.views.generic import RedirectView
from django.views.generic import TemplateView

from agrivision.users.views import custom_login_view, custom_logout_view

urlpatterns = [
    path("", TemplateView.as_view(template_name="pages/home.html"), name="home"),
    path(
        "about/",
        TemplateView.as_view(template_name="pages/about.html"),
        name="about",
    ),
    # Top-level direct login / logout
    path("login/", custom_login_view, name="login"),
    path("logout/", custom_logout_view, name="logout"),
    # Django Admin, use {% url 'admin:index' %}
    path(settings.ADMIN_URL, admin.site.urls),
    # User management
    path("users/", include("agrivision.users.urls", namespace="users")),
    path("accounts/", include("allauth.urls")),
    # AI & Agriculture Module — Member 4
    path("agriculture/", include("agrivision.agriculture.urls", namespace="agriculture")),
    # User Marketplace
    path("marketplace/", include("agrivision.marketplace.urls", namespace="marketplace")),
    # Provider Portal
    path("providers/", include("agrivision.providers.urls", namespace="providers")),
    # Admin Portal
    path("admin-portal/", include("agrivision.admin_portal.urls", namespace="admin_portal")),
    # Media files
    *static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT),
]


if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [
            path("__debug__/", include(debug_toolbar.urls)),
            *urlpatterns,
        ]
