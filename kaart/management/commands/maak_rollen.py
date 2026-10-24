from django.contrib.auth.models import Group, Permission, User
from django.core.management.base import BaseCommand

KIJKERS = "Kaartkijkers"


class Command(BaseCommand):
    help = "Maakt de groep Kaartkijkers (alleen bekijken) en optioneel een gebruiker daarin."

    def add_arguments(self, parser):
        parser.add_argument("--gebruiker", help="gebruikersnaam om in de groep te zetten")
        parser.add_argument("--wachtwoord", help="wachtwoord voor die gebruiker")

    def handle(self, *args, **opts):
        groep, _ = Group.objects.get_or_create(name=KIJKERS)
        rechten = Permission.objects.filter(
            content_type__app_label="kaart", codename__startswith="view_"
        )
        groep.permissions.set(rechten)
        self.stdout.write(
            f"Groep {KIJKERS}: {', '.join(sorted(rechten.values_list('codename', flat=True)))}"
        )
        if opts["gebruiker"]:
            u, _ = User.objects.get_or_create(
                username=opts["gebruiker"], defaults={"is_staff": True}
            )
            u.is_staff = True
            if opts["wachtwoord"]:
                u.set_password(opts["wachtwoord"])
            u.save()
            u.groups.add(groep)
            self.stdout.write(f"Gebruiker {u.username} (is_staff) in {KIJKERS}")
