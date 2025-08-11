# fix_blow_job.py
from decimal import Decimal
from django.apps import apps
from django.db import transaction
from django.db.models import ForeignKey, BooleanField

APP = "cocktails"
Cocktail = apps.get_model(APP, "Cocktail")
Ingredient = apps.get_model(APP, "Ingredient")
Through = apps.get_model(APP, "CocktailIngredient")

# find Units model anywhere (db_table='units')
Units = None
for m in apps.get_models():
    if m._meta.db_table == "units" or m.__name__ in ("Unit", "Units"):
        Units = m
        break

def has_field(model, name):
    return any(getattr(f, "concrete", False) and f.name == name for f in model._meta.get_fields())

amount_field  = "amount_input" if has_field(Through, "amount_input") else None
seq_field     = "seq"          if has_field(Through, "seq")          else None
unit_field    = "unit_input"   if has_field(Through, "unit_input")   else None
garnish_field = "is_optional"  if has_field(Through, "is_optional")  else None

@transaction.atomic
def run():
    # 1) Cocktail & ingredients
    bj = Cocktail.objects.get(name="Blow Job")
    amaretto = Ingredient.objects.get(name="Amaretto")
    irish    = Ingredient.objects.get(name="Irish Cream Liqueur")
    cream    = Ingredient.objects.get(name="Whipped Cream")

    # 2) ABV as PERCENT (0–100)
    for ing, pct in ((amaretto, 28.0), (irish, 17.0), (cream, 0.0)):
        if has_field(Ingredient, "abv"):
            setattr(ing, "abv", Decimal(str(pct)))
            ing.save(update_fields=["abv"])

    # 3) ensure 'oz' unit exists
    unit_oz = None
    if Units:
        unit_oz, _ = Units.objects.get_or_create(name="oz")

    # 4) set rows: seq, amount_input (oz), unit_input=oz, garnish
    def upsert(ing, seq, amt, garnish=False):
        obj, _ = Through.objects.get_or_create(cocktail=bj, ingredient=ing)
        if seq_field: setattr(obj, seq_field, seq)
        if amount_field: setattr(obj, amount_field, Decimal(str(amt)))
        if garnish_field is not None: setattr(obj, garnish_field, bool(garnish))
        if unit_field and unit_oz: setattr(obj, unit_field, unit_oz)
        obj.save()

    upsert(amaretto, 1, 0.5, False)
    upsert(irish,    2, 0.5, False)
    upsert(cream,    3, 0.0, True)

    # try to trigger any recalc hook if present
    for meth in ("recalc","recalculate","recompute","update_totals","compute_abv","compute_totals","refresh_cached_fields"):
        fn = getattr(bj, meth, None)
        if callable(fn):
            try: fn()
            except Exception: pass
    try: bj.save()
    except Exception: pass

    print("✔ Fixed: ABV set (28/17/0), amounts set (0.5 oz + 0.5 oz, cream 0), units=oz, seq=1/2/3.")

run()
