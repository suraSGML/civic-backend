"""
Django filters for the reports module.
"""
import django_filters
from .models import Report, ReportCategory, SeverityLevel, ReportStatus


class ReportFilter(django_filters.FilterSet):
    # Accept both single value (?category=damaged_road) and
    # multiple values (?category=damaged_road&category=waste)
    category = django_filters.CharFilter(field_name='category', lookup_expr='iexact')
    severity = django_filters.CharFilter(field_name='severity', lookup_expr='iexact')
    status = django_filters.CharFilter(field_name='status', lookup_expr='iexact')
    is_emergency = django_filters.BooleanFilter()
    city = django_filters.CharFilter(lookup_expr='icontains')
    region = django_filters.CharFilter(lookup_expr='icontains')
    date_from = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='gte')
    date_to = django_filters.DateTimeFilter(field_name='created_at', lookup_expr='lte')
    lat_min = django_filters.NumberFilter(field_name='latitude', lookup_expr='gte')
    lat_max = django_filters.NumberFilter(field_name='latitude', lookup_expr='lte')
    lng_min = django_filters.NumberFilter(field_name='longitude', lookup_expr='gte')
    lng_max = django_filters.NumberFilter(field_name='longitude', lookup_expr='lte')

    class Meta:
        model = Report
        fields = ['category', 'severity', 'status', 'is_emergency', 'city', 'region']
