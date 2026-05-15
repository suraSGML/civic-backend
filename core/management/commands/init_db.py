"""
Management command to initialize the database.
Runs migrations and seeds data on first startup.
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command


class Command(BaseCommand):
    help = 'Initialize database with migrations and seed data'

    def handle(self, *args, **options):
        self.stdout.write('Running migrations...')
        try:
            call_command('migrate', verbosity=1)
            self.stdout.write(self.style.SUCCESS('✓ Migrations completed'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Migration failed: {e}'))
            return

        self.stdout.write('Seeding data...')
        try:
            call_command('seed_data', verbosity=1)
            self.stdout.write(self.style.SUCCESS('✓ Data seeded'))
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'⚠ Seed data failed (may already exist): {e}'))

        self.stdout.write(self.style.SUCCESS('✓ Database initialization complete'))
