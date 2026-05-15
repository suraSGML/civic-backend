"""
Management command to seed sample data for testing.
Usage: python manage.py seed_data
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
import random


class Command(BaseCommand):
    help = 'Seed the database with sample data for testing'

    def handle(self, *args, **options):
        self.stdout.write('Seeding database...')
        self._create_users()
        self._create_reports()
        self.stdout.write(self.style.SUCCESS('✅ Database seeded successfully!'))

    def _create_users(self):
        from accounts.models import User, UserRole

        users_data = [
            {'email': 'admin@civic.et', 'first_name': 'Admin', 'last_name': 'User',
             'role': UserRole.SUPER_ADMIN, 'password': 'admin123!'},
            {'email': 'authority@civic.et', 'first_name': 'Tigist', 'last_name': 'Haile',
             'role': UserRole.AUTHORITY, 'password': 'auth123!', 'department': 'City Administration'},
            {'email': 'worker1@civic.et', 'first_name': 'Dawit', 'last_name': 'Bekele',
             'role': UserRole.FIELD_WORKER, 'password': 'worker123!',
             'department': 'Roads & Infrastructure', 'employee_id': 'EMP001'},
            {'email': 'worker2@civic.et', 'first_name': 'Meron', 'last_name': 'Tadesse',
             'role': UserRole.FIELD_WORKER, 'password': 'worker123!',
             'department': 'Utilities', 'employee_id': 'EMP002'},
            {'email': 'citizen1@civic.et', 'first_name': 'Abebe', 'last_name': 'Girma',
             'role': UserRole.CITIZEN, 'password': 'citizen123!'},
            {'email': 'citizen2@civic.et', 'first_name': 'Hana', 'last_name': 'Tesfaye',
             'role': UserRole.CITIZEN, 'password': 'citizen123!'},
        ]

        for data in users_data:
            password = data.pop('password')
            user, created = User.objects.get_or_create(email=data['email'], defaults=data)
            if created:
                user.set_password(password)
                user.is_verified = True
                user.save()
                self.stdout.write(f'  Created user: {user.email}')

    def _create_reports(self):
        from accounts.models import User, UserRole
        from reports.models import Report, ReportCategory, SeverityLevel, ReportStatus

        citizens = list(User.objects.filter(role=UserRole.CITIZEN))
        if not citizens:
            return

        # Bahir Dar area coordinates
        base_lat, base_lng = 11.5936, 37.3906

        sample_reports = [
            {
                'title': 'Large pothole on Kebele 12 main road',
                'description': 'There is a very large pothole on the main road near the market. It has caused several accidents and is dangerous for vehicles.',
                'category': ReportCategory.DAMAGED_ROAD,
                'severity': SeverityLevel.HIGH,
            },
            {
                'title': 'Street lights not working near hospital',
                'description': 'Multiple street lights near Felege Hiwot Hospital have been broken for 2 weeks. The area is very dark at night.',
                'category': ReportCategory.BROKEN_STREETLIGHT,
                'severity': SeverityLevel.MEDIUM,
            },
            {
                'title': 'No water supply for 3 days',
                'description': 'Our neighborhood has had no water supply for 3 days. Residents are struggling to get water.',
                'category': ReportCategory.WATER_SUPPLY,
                'severity': SeverityLevel.CRITICAL,
            },
            {
                'title': 'Garbage pile blocking road',
                'description': 'A large pile of garbage has accumulated near the school and is blocking part of the road.',
                'category': ReportCategory.WASTE,
                'severity': SeverityLevel.MEDIUM,
            },
            {
                'title': 'Power outage in residential area',
                'description': 'Electricity has been out since yesterday morning in our area. Businesses and homes are affected.',
                'category': ReportCategory.ELECTRICITY,
                'severity': SeverityLevel.HIGH,
            },
            {
                'title': 'Suspicious activity near market',
                'description': 'Suspicious individuals have been seen near the market at night. Residents are concerned.',
                'category': ReportCategory.CRIME,
                'severity': SeverityLevel.HIGH,
            },
            {
                'title': 'Traffic accident on main highway',
                'description': 'A serious traffic accident occurred. Two vehicles involved, injuries reported.',
                'category': ReportCategory.ACCIDENT,
                'severity': SeverityLevel.CRITICAL,
            },
        ]

        for i, data in enumerate(sample_reports):
            lat = base_lat + (random.random() - 0.5) * 0.05
            lng = base_lng + (random.random() - 0.5) * 0.05
            report, created = Report.objects.get_or_create(
                title=data['title'],
                defaults={
                    **data,
                    'reporter': random.choice(citizens),
                    'latitude': Decimal(str(round(lat, 6))),
                    'longitude': Decimal(str(round(lng, 6))),
                    'address': f'Kebele {random.randint(1, 20)}, Bahir Dar',
                    'city': 'Bahir Dar',
                    'region': 'Amhara',
                }
            )
            if created:
                self.stdout.write(f'  Created report: {report.title[:50]}')
