from django.contrib import admin
from .models import Report, ReportComment, ReportUpvote, StatusHistory


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'category', 'severity', 'status',
                    'reporter', 'is_emergency', 'created_at']
    list_filter = ['category', 'severity', 'status', 'is_emergency', 'city']
    search_fields = ['title', 'description', 'address']
    readonly_fields = ['created_at', 'updated_at', 'resolved_at']
    date_hierarchy = 'created_at'


@admin.register(ReportComment)
class ReportCommentAdmin(admin.ModelAdmin):
    list_display = ['id', 'report', 'author', 'is_public', 'created_at']
    list_filter = ['is_public']


@admin.register(ReportUpvote)
class ReportUpvoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'report', 'user', 'created_at']


@admin.register(StatusHistory)
class StatusHistoryAdmin(admin.ModelAdmin):
    list_display = ['id', 'report', 'old_status', 'new_status', 'changed_by', 'changed_at']
    list_filter = ['old_status', 'new_status']
