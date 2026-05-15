from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, PasswordResetToken, EmailVerificationToken


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ['email', 'get_full_name', 'role', 'is_active', 'is_verified', 'date_joined']
    list_filter = ['role', 'is_active', 'is_verified', 'is_banned']
    search_fields = ['email', 'first_name', 'last_name', 'phone']
    ordering = ['-date_joined']
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal Info', {'fields': ('first_name', 'last_name', 'phone', 'avatar', 'bio')}),
        ('Location', {'fields': ('city', 'region', 'latitude', 'longitude')}),
        ('Role & Status', {'fields': ('role', 'is_active', 'is_verified', 'is_banned', 'ban_reason')}),
        ('Worker Info', {'fields': ('department', 'employee_id', 'specialization')}),
        ('Permissions', {'fields': ('is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Notifications', {'fields': ('notify_email', 'notify_sms', 'notify_push')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'first_name', 'last_name', 'role', 'password1', 'password2'),
        }),
    )


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used']


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ['user', 'created_at', 'expires_at', 'is_used']
    list_filter = ['is_used']
