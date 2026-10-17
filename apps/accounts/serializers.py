from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Public representation of a user (output only).

    Notice what is NOT here: password, is_superuser, groups, permissions.
    A serializer is an allow-list. Only fields listed in `fields` are exposed.
    """

    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "full_name", "date_joined"]
        read_only_fields = fields


class RegisterSerializer(serializers.ModelSerializer):
    """Validates sign-up data and creates the user."""

    password = serializers.CharField(
        write_only=True,  # accepted as input, never included in output
        style={"input_type": "password"},
        trim_whitespace=False,
    )
    password_confirm = serializers.CharField(
        write_only=True, style={"input_type": "password"}, trim_whitespace=False
    )

    class Meta:
        model = User
        fields = ["id", "email", "first_name", "last_name", "password", "password_confirm"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "first_name": {"required": True, "allow_blank": False},
            "last_name": {"required": True, "allow_blank": False},
            # We validate uniqueness ourselves (case-insensitively) below,
            # so disable the model's case-sensitive auto-generated validator.
            "email": {"validators": []},
        }

    # Field-level validation: runs for one field, method name = validate_<field>.
    def validate_email(self, value: str) -> str:
        email = value.strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return email

    # Object-level validation: runs after all fields pass, sees them together.
    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})

        # Run Django's AUTH_PASSWORD_VALIDATORS. Passing an unsaved user lets the
        # similarity validator reject passwords too close to the email or name.
        candidate = User(
            email=attrs["email"],
            first_name=attrs.get("first_name", ""),
            last_name=attrs.get("last_name", ""),
        )
        try:
            validate_password(attrs["password"], user=candidate)
        except DjangoValidationError as exc:  # Django's error type, converted to DRF's
            raise serializers.ValidationError({"password": list(exc.messages)})
        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")
        password = validated_data.pop("password")
        # Go through the manager so the password is hashed and email normalised.
        return User.objects.create_user(password=password, **validated_data)


class UserUpdateSerializer(serializers.ModelSerializer):
    """
    Fields a user may change about themselves.

    Only names are writable. Email, is_staff, is_superuser etc. are simply not
    listed, so a request like {"is_staff": true} is silently ignored. This is
    how serializers prevent "mass assignment" attacks.
    """

    class Meta:
        model = User
        fields = ["first_name", "last_name"]
        extra_kwargs = {
            "first_name": {"allow_blank": False},
            "last_name": {"allow_blank": False},
        }


class ChangePasswordSerializer(serializers.Serializer):
    """
    A plain Serializer (not ModelSerializer) because this is an action, not a
    representation of a model: the input fields don't map to model fields.
    """

    old_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password = serializers.CharField(write_only=True, trim_whitespace=False)
    new_password_confirm = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_old_password(self, value: str) -> str:
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        if attrs["new_password"] == attrs["old_password"]:
            raise serializers.ValidationError(
                {"new_password": "New password must be different from the current password."}
            )
        try:
            validate_password(attrs["new_password"], user=self.context["request"].user)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"new_password": list(exc.messages)})
        return attrs


class LogoutSerializer(serializers.Serializer):
    """Accepts a refresh token and checks that it belongs to the caller."""

    refresh = serializers.CharField(write_only=True)

    def validate_refresh(self, value: str) -> RefreshToken:
        try:
            token = RefreshToken(value)  # verifies signature and expiry; raises if blacklisted
        except TokenError:
            raise serializers.ValidationError("Token is invalid, expired or already revoked.")

        # Without this check, anyone holding someone else's refresh token could
        # log that person out. Compare as strings: the claim may be stored as str.
        user = self.context["request"].user
        if str(token.get("user_id")) != str(user.pk):
            raise serializers.ValidationError("Token does not belong to the current user.")
        return token
