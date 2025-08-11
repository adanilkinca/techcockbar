# set_amounts.py
from decimal import Decimal
from django.apps import apps
from django.db import transaction
from django.db.models import ForeignKey, BooleanField

APP = "cocktails"
Through = apps.get_model(APP, "CocktailIngredient")
Ingredient = apps.get_model(APP, "Ingredient")
Cocktail = apps.get_model(APP, "Cocktail")

# 1) pick a numeric amount field
def candidate_amount_field():
    prefs = [
        "amount_ml","amount","quantity_ml","quantity","input_amount","input_value",
        "value_ml","volume_ml","volume","measure","portion","value","dose","size","count"
    ]
    numeric_types = {"DecimalField","FloatField","IntegerField","PositiveIntegerField","SmallIntegerField","PositiveSmallIntegerField"}
    fields = [f for f in Through._meta.get_fields() if getattr(f,"concrete",False)]
    # prefer known names
    names = {f.name: f for f in fields}
    for p in prefs:
        if p in names and names[p].get_internal_type() in numeric_types:
            return p
    # else: first numeric non-FK, non-boolean
    for f in fields:
        if isinstance(f, (ForeignKey, BooleanField)): 
            continue
        if f.get_internal_type() in numeric_types and f.name not in ("id",):
            return f.name
    return None

amount_field = candidate_amount_field()
if not amount_field:
    raise SystemExit("No numeric amount field found on CocktailIngredient. Please tell me the field list, and I’ll wire it.")

@transaction.atomic
def run():
    bj = Cocktail.objects.get(name="Blow Job")
    def ing(n): return Ingredient.objects.get(name=n)

    rows = [
        (ing("Amaretto"), Decimal("15"), False),
        (ing("Irish Cream Liqueur"), Decimal("15"), False),
        (ing("Whipped Cream"), Decimal("5"), True),
    ]
    created = []
    for ingredient, amt, garnish in rows:
        obj, _ = Through.objects.get_or_create(cocktail=bj, ingredient=ingredient)
        setattr(obj, amount_field, amt)
        # try both common garnish names
        if hasattr(obj, "is_garnish"): obj.is_garnish = garnish
        if hasattr(obj, "garnish"): obj.garnish = garnish
        if hasattr(obj, "is_optional"): obj.is_optional = garnish
        obj.save()
        created.append((obj.id, ingredient.name, amt, garnish))
    return created

rows = run()
print("✔ Amounts set using field:", amount_field)
print("Rows:", rows)
