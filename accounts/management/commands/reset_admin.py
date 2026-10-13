import getpass
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Emergency CLI utility to reset an Administrator account password without needing email."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            type=str,
            help="Username of the administrator account to reset.",
        )
        parser.add_argument(
            "--password",
            type=str,
            help="New password for the administrator account (optional; if omitted, you will be prompted).",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== RespiScan Emergency Admin Password Reset ===\n"))

        username = options.get("username")
        password = options.get("password")

        # 1. Locate the target user
        if username:
            try:
                target_user = User.objects.get(username__iexact=username)
            except User.DoesNotExist:
                raise CommandError(f"No user found with username: '{username}'")
        else:
            # Query all administrators
            admins = list(User.objects.filter(role="admin") | User.objects.filter(is_superuser=True))
            # Deduplicate by pk
            seen = set()
            unique_admins = []
            for u in admins:
                if u.pk not in seen:
                    seen.add(u.pk)
                    unique_admins.append(u)

            if not unique_admins:
                self.stdout.write(self.style.WARNING("No administrator accounts found in the database."))
                create_new = input("Would you like to create a new administrator account now? (y/n): ").strip().lower()
                if create_new == "y":
                    new_user = input("Enter admin username: ").strip()
                    new_email = input("Enter admin email: ").strip()
                    new_pwd = getpass.getpass("Enter password (min 8 chars): ").strip()
                    if len(new_pwd) < 8:
                        raise CommandError("Password must be at least 8 characters long.")
                    user = User.objects.create_superuser(
                        username=new_user,
                        email=new_email,
                        password=new_pwd,
                        role="admin"
                    )
                    self.stdout.write(self.style.SUCCESS(f"\nSuccessfully created administrator '{user.username}'!"))
                    return
                else:
                    return

            self.stdout.write("Discovered Administrator Accounts:")
            for idx, admin_user in enumerate(unique_admins, 1):
                full_name = f"{admin_user.first_name} {admin_user.last_name}".strip()
                display_name = f" ({full_name})" if full_name else ""
                status_str = "Active" if admin_user.is_active else "Inactive"
                self.stdout.write(f"  [{idx}] {admin_user.username}{display_name} - {admin_user.email or 'No email'} [{status_str}]")

            if len(unique_admins) == 1:
                target_user = unique_admins[0]
                self.stdout.write(f"\nSelecting sole administrator: '{target_user.username}'")
            else:
                choice = input(f"\nSelect account to reset [1-{len(unique_admins)}]: ").strip()
                try:
                    choice_idx = int(choice) - 1
                    if not (0 <= choice_idx < len(unique_admins)):
                        raise ValueError()
                    target_user = unique_admins[choice_idx]
                except ValueError:
                    raise CommandError("Invalid selection.")

        # 2. Get new password
        if not password:
            while True:
                p1 = getpass.getpass(f"\nEnter new password for '{target_user.username}' (min 8 characters): ")
                if len(p1) < 8:
                    self.stdout.write(self.style.ERROR("Error: Password must be at least 8 characters long."))
                    continue
                p2 = getpass.getpass("Confirm new password: ")
                if p1 != p2:
                    self.stdout.write(self.style.ERROR("Error: Passwords do not match. Try again."))
                    continue
                password = p1
                break
        else:
            if len(password) < 8:
                raise CommandError("Password must be at least 8 characters long.")

        # 3. Update account credentials
        target_user.set_password(password)
        target_user.is_active = True
        target_user.role = "admin"
        target_user.is_staff = True
        target_user.save()

        self.stdout.write(self.style.SUCCESS(f"\nSUCCESS: Password for administrator '{target_user.username}' has been updated."))
        self.stdout.write(self.style.SUCCESS(f"The account is ACTIVE and ready to log in immediately at the Clinical Portal.\n"))
