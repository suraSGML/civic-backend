from django.contrib import admin
from .models import MediaFile


@admin.register(MediaFile)
class MediaFileAdmin(admin.ModelAdmin):
    list_display = ['id', 'report', 'media_type', 'original_filename',
                    'is_verified', 'is_flagged', 'created_at']
    list_filter = ['media_type', 'is_verified', 'is_flagged']
    search_fields = ['original_filename', 'report__title']
