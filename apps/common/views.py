from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response


@extend_schema(
    summary="Health check",
    description="Returns 200 when the API process is running. Requires no authentication.",
    responses={
        200: inline_serializer(
            name="HealthCheckResponse",
            fields={"status": serializers.CharField(), "service": serializers.CharField()},
        )
    },
)
@api_view(["GET"])
@authentication_classes([])      # no login needed, and no session/DB lookup
@permission_classes([AllowAny])  # explicitly opts out of the IsAuthenticated default
@throttle_classes([])            # monitoring tools ping this often; never rate-limit it
def health_check(request: Request) -> Response:
    return Response({"status": "ok", "service": "taskflow-api"}, status=status.HTTP_200_OK)
