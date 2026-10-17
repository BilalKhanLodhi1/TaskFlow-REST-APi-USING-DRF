from django.contrib.auth import get_user_model
from drf_spectacular.utils import extend_schema
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from . import services
from .serializers import (
    ChangePasswordSerializer,
    LogoutSerializer,
    RegisterSerializer,
    UserSerializer,
    UserUpdateSerializer,
)

User = get_user_model()


class AuthThrottleMixin:
    """Applies the strict "auth" rate limit (e.g. 10/minute per client)."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


@extend_schema(tags=["Auth"], summary="Register a new account", responses={201: UserSerializer})
class RegisterView(AuthThrottleMixin, generics.CreateAPIView):
    """
    POST /api/v1/auth/register/

    CreateAPIView supplies the whole flow: validate input with the serializer,
    call serializer.save(), return 201. We only override the response so it
    uses UserSerializer (no password fields).
    """

    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    authentication_classes = []  # registering never requires (or uses) a token

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data, status=status.HTTP_201_CREATED)


@extend_schema(tags=["Auth"], summary="Log in: obtain access and refresh tokens")
class LoginView(AuthThrottleMixin, TokenObtainPairView):
    """POST /api/v1/auth/token/  body: {"email": ..., "password": ...}"""


@extend_schema(tags=["Auth"], summary="Exchange a refresh token for new tokens")
class RefreshView(AuthThrottleMixin, TokenRefreshView):
    """POST /api/v1/auth/token/refresh/  body: {"refresh": ...}"""


@extend_schema(tags=["Auth"], summary="Log out: revoke a refresh token", responses={204: None})
class LogoutView(generics.GenericAPIView):
    """
    POST /api/v1/auth/logout/  body: {"refresh": ...}

    JWTs are stateless, so "logging out" means blacklisting the refresh token.
    The current access token keeps working until it expires (max 15 minutes);
    the client should also delete both tokens from its storage.
    """

    serializer_class = LogoutSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.validated_data["refresh"].blacklist()
        return Response(status=status.HTTP_204_NO_CONTENT)


@extend_schema(tags=["Auth"])
class MeView(generics.RetrieveUpdateAPIView):
    """
    GET   /api/v1/auth/me/   -> your profile
    PATCH /api/v1/auth/me/   -> update first_name / last_name

    PUT is disabled: a full replacement makes little sense for a profile where
    most fields are server-controlled.
    """

    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "patch", "head", "options"]

    def get_object(self):
        # No ID in the URL: "me" is always the authenticated user, so there is
        # no way to request someone else's profile through this endpoint.
        return self.request.user

    def get_serializer_class(self):
        if self.request.method == "PATCH":
            return UserUpdateSerializer
        return UserSerializer

    @extend_schema(summary="Get your profile", responses={200: UserSerializer})
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Update your profile",
        request=UserUpdateSerializer,
        responses={200: UserSerializer},
    )
    def patch(self, request, *args, **kwargs):
        serializer = UserUpdateSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(UserSerializer(user).data)


@extend_schema(tags=["Auth"], summary="Change your password", responses={204: None})
class ChangePasswordView(AuthThrottleMixin, generics.GenericAPIView):
    """
    POST /api/v1/auth/change-password/

    After a successful change, ALL of the user's refresh tokens are revoked,
    so every device must log in again. This protects users who change their
    password because they suspect someone else has access.
    """

    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        services.change_password(request.user, serializer.validated_data["new_password"])
        return Response(status=status.HTTP_204_NO_CONTENT)
