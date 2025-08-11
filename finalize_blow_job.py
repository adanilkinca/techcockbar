# finalize_blow_job.py
from decimal import Decimal
from django.apps import apps
from django.db import transaction
from django.db.models import ForeignKey, BooleanField

APP = "cocktails"

Cocktail = apps.get_model(APP, "Cocktail")
Ingredient = apps.get_model(APP, "Ingredient")
Through = apps.get_model(APP, "CocktailIngredient")

# --- find or pick fields dynamically ---
def fields(model):
    return [f for f in model._meta.get_fields() if getattr(f, "concrete", False)]

def pick_amount_field():
    prefs = ["amount_ml","amount","quantity_ml","quantity","input_amount","input_value",
             "value_ml","volume_ml","volume","measure","portion","value","dose","size","count"]
    numeric_types = {"DecimalField","FloatField","IntegerField","PositiveIntegerField","SmallIntegerField","PositiveSmallIntegerField"}
    byname = {f.name:f for f in fields(Through)}
    for p in prefs:
        if p in byname and byname[p].get_internal_type() in numeric_types:
            return p
    for f in fields(Through):
        if isinstance(f, (ForeignKey, BooleanField)): continue
        if f.get_internal_type() in numeric_types and f.name not in ("id",):
            return f.name
    return None

def pick_garnish_field():
    for name in ["is_garnish","garnish","is_optional"]:
        if any(f.name==name and isinstance(f, BooleanField) for f in fields(Through)):
            return name
    return None

def pick_unit_field():
    # FK to a Unit/Units model; your schema showed unit_input
    for name in ["unit_input","unit","input_unit","measure_unit"]:
        if any(f.name==name and isinstance(f, ForeignKey) for f in fields(Through)):
            return name
    return None

def find_units_model():
    for m in apps.get_models():
        if m._meta.db_table == "units" or m.__name__ in ("Unit","Units"):
            return m
    return None

def pick_ing_abv_field():
    # try common names on Ingredient for alcohol strength
    for name in ["abv","alcohol_by_volume","alcohol","strength","abv_percent","alcohol_percent","alcohol_pct"]:
        for f in fields(Ingredient):
            if f.name == name and f.get_internal_type() in ("DecimalField","FloatField","IntegerField","PositiveIntegerField","SmallIntegerField"):
                return name
    return None

amount_field = pick_amount_field()
garnish_field = pick_garnish_field()
unit_field = pick_unit_field()
Units = find_units_model()
abv_field = pick_ing_abv_field()

@transaction.atomic
def run():
    out = {"amount_field":amount_field, "garnish_field":garnish_field, "unit_field":unit_field, "ingredient_abv_field":abv_field}
    # 1) ensure unit 'ml'
    ml = None
    if Units:
        ml, _ = Units.objects.get_or_create(name="ml")
    # 2) upsert ingredients + set ABV if possible
    def get_ing(name, abv_val=None):
        ing, _ = Ingredient.objects.get_or_create(name=name)
        if abv_field and abv_val is not None:
            # Heuristic: if someone stores % as 0–1 scale, they likely have existing values <= 1
            scale_as_fraction = False
            sample = Ingredient.objects.exclude(**{abv_field: None}).values_list(abv_field, flat=True)[:1]
            if sample and sample[0] is not None and float(sample[0]) <= 1.0:
                scale_as_fraction = True
            val = abv_val if scale_as_fraction else (abv_val*100 if abv_val <= 1 else abv_val)
            setattr(ing, abv_field, val)
            ing.save(update_fields=[abv_field])
        return ing

    amaretto = get_ing("Amaretto", 0.28)
    irish    = get_ing("Irish Cream Liqueur", 0.17)
    cream    = get_ing("Whipped Cream", 0.0)

    # 3) get cocktail
    ckt, _ = Cocktail.objects.get_or_create(name="Blow Job")

    # 4) link rows with amounts + garnish + unit
    if not amount_field:
        out["error"] = "No numeric amount field found on through model; cannot set volumes."
        return out

    def upsert(ing, amt, garnish=False):
        obj, _ = Through.objects.get_or_create(cocktail=ckt, ingredient=ing)
        setattr(obj, amount_field, Decimal(str(amt)))
        if garnish_field is not None:
            setattr(obj, garnish_field, bool(garnish))
        if unit_field and Units and ml:
            setattr(obj, unit_field, ml)
        obj.save()

    upsert(amaretto, 15, False)
    upsert(irish,    15, False)
    upsert(cream,     5, True)

    # 5) try to trigger any recalculation hooks if your model has them
    for meth in ["recalc","recalculate","recompute","update_totals","compute_abv","compute_totals","refresh_cached_fields"]:
        fn = getattr(ckt, meth, None)
        if callable(fn):
            try:
                fn()
            except Exception:
                pass
    # Save once more (if signals compute values on save)
    try:
        ckt.save()
    except Exception:
        pass

    # 6) quick expected ABV calc (excluding garnish): (15*0.28 + 15*0.17) / 30 = 0.225 → 22.5%
    pure_ml = 15*0.28 + 15*0.17
    abv_expected = pure_ml / 30
    out["abv_expected_fraction"] = round(abv_expected, 4)
    out["abv_expected_percent"] = round(abv_expected*100, 2)
    return out

info = run()
print("Finalize result:", info)
