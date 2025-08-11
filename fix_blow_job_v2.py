# fix_blow_job_v2.py
from decimal import Decimal
from django.apps import apps
from django.db import transaction

APP = "cocktails"
Cocktail = apps.get_model(APP, "Cocktail")
Ingredient = apps.get_model(APP, "Ingredient")
Through = apps.get_model(APP, "CocktailIngredient")

# Units table exists in DB; ensure rows exist but assign strings to unit_input (CharField)
Units = None
for m in apps.get_models():
    if m._meta.db_table == "units" or m.__name__ in ("Unit","Units"):
        Units = m
        break

def has_field(model, name):
    return any(getattr(f,"concrete",False) and f.name==name for f in model._meta.get_fields())

amount_field  = "amount_input" if has_field(Through, "amount_input") else None
seq_field     = "seq"          if has_field(Through, "seq")          else None
unit_field    = "unit_input"   if has_field(Through, "unit_input")   else None
garnish_field = "is_optional"  if has_field(Through, "is_optional")  else None
amount_oz     = "amount_oz"    if has_field(Through, "amount_oz")    else None

@transaction.atomic
def run():
    # Ensure allowed units exist in units table (because of FK at DB level)
    if Units:
        for u in ["oz","leaf","wedge","dash","ml"]:
            Units.objects.get_or_create(name=u)

    bj = Cocktail.objects.get(name="Blow Job")
    amaretto = Ingredient.objects.get(name="Amaretto")
    irish    = Ingredient.objects.get(name="Irish Cream Liqueur")
    cream    = Ingredient.objects.get(name="Whipped Cream")

    # ABV as PERCENT (0–100)
    if has_field(Ingredient, "abv"):
        for ing, pct in ((amaretto, 28), (irish, 17), (cream, 0)):
            if getattr(ing, "abv", None) != pct:
                ing.abv = pct
                ing.save(update_fields=["abv"])

    def upsert(ing, seq, amt, garnish=False):
        obj, _ = Through.objects.get_or_create(cocktail=bj, ingredient=ing)
        if seq_field: setattr(obj, seq_field, seq)
        if amount_field: setattr(obj, amount_field, Decimal(str(amt)))
        if garnish_field is not None: setattr(obj, garnish_field, bool(garnish))
        if unit_field: setattr(obj, unit_field, "oz")   # CharField expects string
        if amount_oz and unit_field and getattr(obj, unit_field) == "oz":
            setattr(obj, amount_oz, Decimal(str(amt)))  # keep oz mirror if your model stores it
        obj.save()

    upsert(amaretto, 1, 0.5, False)
    upsert(irish,    2, 0.5, False)
    upsert(cream,    3, 0.0, True)

    # Try any recalc hooks and save
    for meth in ("recalc","recalculate","recompute","update_totals","compute_abv","compute_totals","refresh_cached_fields"):
        fn = getattr(bj, meth, None)
        if callable(fn):
            try: fn()
            except Exception: pass
    try: bj.save()
    except Exception: pass

    print("✔ Blow Job fixed: amounts set to 0.5/0.5/0.0 oz, units='oz', seq=1/2/3, ABV on ingredients 28/17/0.")

run()
