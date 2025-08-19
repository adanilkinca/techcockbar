from decimal import Decimal
from django.core.management.base import BaseCommand
from cocktails.models import CocktailIngredient


def to_oz(amount, unit):
    if amount is None:
        return Decimal("0")
    unit = (unit or "").lower()
    amt = Decimal(str(amount))
    if unit == "oz":
        return amt
    if unit == "ml":
        return amt / Decimal("29.5735")
    return Decimal("0")


class Command(BaseCommand):
    help = "Backfill CocktailIngredient.amount_oz from amount_input + unit_input"

    def handle(self, *args, **options):
        updated = 0
        for ci in CocktailIngredient.objects.all():
            new_val = to_oz(ci.amount_input, getattr(ci, "unit_input", None))
            if ci.amount_oz != new_val:
                ci.amount_oz = new_val
                ci.save(update_fields=["amount_oz"])
                updated += 1
        self.stdout.write(self.style.SUCCESS(f"Updated rows: {updated}"))
