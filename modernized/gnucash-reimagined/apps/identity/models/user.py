"""
User domain model.

Represents a platform user with authentication and profile information.
"""
import uuid
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Manager for the email-as-username custom user model.

    Django's stock ``UserManager.create_user`` takes ``username`` as its first
    positional argument, which cannot work for a model whose ``USERNAME_FIELD``
    is ``email`` - every ``User.objects.create_user(email=..., ...)`` call site
    would raise TypeError. A custom user model with a non-username identifier
    requires a matching manager, so this replaces the inherited one.

    ``use_in_migrations`` mirrors Django's own manager so that historical
    migrations keep a stable reference to it.
    """

    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """Create and save a user with the given email and password."""
        if not email:
            raise ValueError("Users must have an email address")
        email = self.normalize_email(email)
        # `username` is inherited from AbstractUser and is UNIQUE, so it must be
        # populated for every user. Deriving it from the email keeps that
        # constraint satisfiable without forcing callers to supply a value that
        # is no longer the login identifier.
        extra_fields.setdefault("username", email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        """Create a regular user (is_staff/is_superuser default to False)."""
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        """Create a superuser, enforcing the staff/superuser flags."""
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    """
    Platform user with authentication and profile information.

    Extends Django's AbstractUser to provide:
    - UUID primary key (guid)
    - Email as username field
    - Profile information
    - MFA enrollment tracking
    - Audit fields

    This is the custom user model for the identity app, configured via
    AUTH_USER_MODEL = "identity.User" in Django settings.
    """

    guid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True, blank=False, null=False)

    # Profile information
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)
    phone_number = models.CharField(max_length=50, blank=True)
    timezone = models.CharField(max_length=50, default='UTC')
    language = models.CharField(max_length=10, default='en')

    # MFA enrollment
    mfa_enabled = models.BooleanField(default=False)
    mfa_enrolled_at = models.DateTimeField(null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_verified = models.BooleanField(default=False)
    verified_at = models.DateTimeField(null=True, blank=True)

    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return self.email

    @property
    def full_name(self):
        """Return user's full name."""
        return f'{self.first_name} {self.last_name}'.strip() or self.email
