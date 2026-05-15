"""
User models for the Civic System.
Supports multi-role: Citizen, Field Worker, Authority, Super Admin.
"""
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
from phonenumber_field.modelfields import PhoneNumberField


class UserRole(models.TextChoices):
    CITIZEN = 'citizen', 'Citizen'
    FIELD_WORKER = 'field_worker', 'Field Worker'
    AUTHORITY = 'authority', 'Authority'
    SUPER_ADMIN = 'super_admin', 'Super Admin'


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Email address is required')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('role', UserRole.SUPER_ADMIN)
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_verified', True)
        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    Custom user model supporting multi-role civic system.
    """
    email = models.EmailField(unique=True, db_index=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    phone = PhoneNumberField(blank=True, null=True)
    role = models.CharField(
        max_length=20,
        choices=UserRole.choices,
        default=UserRole.CITIZEN,
        db_index=True,
    )
    avatar = models.ImageField(upload_to='avatars/', blank=True, null=True)
    bio = models.TextField(blank=True)

    # Location
    city = models.CharField(max_length=100, blank=True, default='Bahir Dar')
    region = models.CharField(max_length=100, blank=True, default='Amhara')
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)

    # Status
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    is_banned = models.BooleanField(default=False)
    ban_reason = models.TextField(blank=True)

    # Worker-specific
    department = models.CharField(max_length=200, blank=True)
    employee_id = models.CharField(max_length=50, blank=True)
    specialization = models.CharField(max_length=200, blank=True)

    # Timestamps
    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Notification preferences
    notify_email = models.BooleanField(default=True)
    notify_sms = models.BooleanField(default=True)
    notify_push = models.BooleanField(default=True)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-date_joined']

    def __str__(self):
        return f'{self.get_full_name()} ({self.role})'

    def get_full_name(self):
        return f'{self.first_name} {self.last_name}'.strip()

    @property
    def is_citizen(self):
        return self.role == UserRole.CITIZEN

    @property
    def is_field_worker(self):
        return self.role == UserRole.FIELD_WORKER

    @property
    def is_authority(self):
        return self.role == UserRole.AUTHORITY

    @property
    def is_super_admin(self):
        return self.role == UserRole.SUPER_ADMIN

    @property
    def can_manage_reports(self):
        return self.role in [UserRole.AUTHORITY, UserRole.SUPER_ADMIN]


class PasswordResetToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = 'password_reset_tokens'

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at


class EmailVerificationToken(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='verification_tokens')
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)

    class Meta:
        db_table = 'email_verification_tokens'

    def is_valid(self):
        return not self.is_used and timezone.now() < self.expires_at
