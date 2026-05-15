from django.contrib import admin
from .models import Assignment, EmergencyDispatch


@admin.register(Assignment)
class AssignmentAdmin(admin.ModelAdmin):
    list_display = ['id', 'report', 'worker', 'assigned_by', 'status', 'priority', 'assigned_at']
    list_filter = ['status', 'priority']
    search_fields = ['report__title', 'worker__email']
    date_hierarchy = 'assigned_at'


@admin.register(EmergencyDispatch)
class EmergencyDispatchAdmin(admin.ModelAdmin):
    list_display = ['id', 'report', 'dispatch_type', 'unit_name', 'dispatched_at', 'arrived_at']
    list_filter = ['dispatch_type']
