"""
Custom DRF permissions for role-based access control.
"""
from rest_framework.permissions import BasePermission
from accounts.models import UserRole


class IsAdminOrSuperAdmin(BasePermission):
    """Allow access only to Authority and Super Admin users."""
    message = 'Access restricted to authority users.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in [UserRole.AUTHORITY, UserRole.SUPER_ADMIN]
        )


class IsSuperAdmin(BasePermission):
    """Allow access only to Super Admin users."""
    message = 'Access restricted to super administrators.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == UserRole.SUPER_ADMIN
        )


class IsFieldWorker(BasePermission):
    """Allow access only to Field Workers."""
    message = 'Access restricted to field workers.'

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role == UserRole.FIELD_WORKER
        )


class IsOwnerOrAdmin(BasePermission):
    """Allow access to object owner or admin."""
    def has_object_permission(self, request, view, obj):
        if request.user.can_manage_reports:
            return True
        return getattr(obj, 'reporter', None) == request.user or \
               getattr(obj, 'user', None) == request.user


class IsWorkerOrAdmin(BasePermission):
    """Allow access to field workers and admins."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated and
            request.user.role in [
                UserRole.FIELD_WORKER,
                UserRole.AUTHORITY,
                UserRole.SUPER_ADMIN,
            ]
        )
