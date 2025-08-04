from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password, identify_hasher
from app.models import User

class Command(BaseCommand):
    help = 'Hashes all plain text passwords in the User table that are not already hashed.'

    def handle(self, *args, **options):
        updated = 0
        for user in User.objects.all():
            try:
                identify_hasher(user.password)
            except Exception:
                self.stdout.write(f"Hashing password for user: {user.username}")
                user.password = make_password(user.password)
                user.save()
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"Updated {updated} user(s) with hashed passwords."))
