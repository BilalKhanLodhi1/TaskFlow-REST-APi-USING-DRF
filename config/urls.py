"""
Root URL configuration.

All API routes live under /api/v1/ so a future, incompatible version can be
added as /api/v2/ without breaking existing clients.
"""

from django.conf import settings
from django.views.generic import RedirectView
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

api_v1_patterns = [
    path("", include("apps.common.urls")),
    # Phase 2+: path("auth/", include("apps.accounts.urls")), etc.
]

urlpatterns = [
    path("", RedirectView.as_view(pattern_name="swagger-ui", permanent=False)),
    path("admin/", admin.site.urls),
    path("api/v1/", include(api_v1_patterns)),
    # OpenAPI schema and interactive documentation
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]

# Serve uploaded files through Django ONLY during local development.
# Phase 7 replaces this with permission-checked downloads.
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
