from django.contrib import admin
from .models import AuditLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'action', 'ip_address', 'status_code', 'timestamp']
    list_filter = ['status_code']
    search_fields = ['user__email', 'action', 'ip_address']
    date_hierarchy = 'timestamp'
    readonly_fields = ['user', 'action', 'ip_address', 'user_agent',
                       'status_code', 'extra_data', 'timestamp']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
