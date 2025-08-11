from decimal import Decimal
from django.apps import apps
from django.db import transaction
from django.utils import timezone
from django.db.models import (
    IntegerField, PositiveIntegerField, SmallIntegerField, PositiveSmallIntegerField,
    FloatField, DecimalField, BooleanField, CharField, TextField, ForeignKey,
    DateTimeField, DateField, TimeField
)

APP = "cocktails"

BLOW_JOB_IMG = "https://res.cloudinary.com/dau9qbp3l/image/upload/v1754790155/blow_job-master.jpg"
INGR_IMG = {
    "Amaretto": "https://res.cloudinary.com/dau9qbp3l/image/upload/v1754790212/amaretto_liqueur-master.webp",
    "Irish Cream Liqueur": "https://res.cloudinary.com/dau9qbp3l/image/upload/v1754790215/irish_cream_liqueur-master.webp",
    "Whipped Cream": "https://res.cloudinary.com/dau9qbp3l/image/upload/v1754790221/whipped-cream-master.webp",
}

Ingredient = apps.get_model(APP, "Ingredient")
Cocktail   = apps.get_model(APP, "Cocktail")

# -------- locate through model --------
def find_through_model():
    for m in apps.get_models():
        fks = [f for f in m._meta.get_fields() if getattr(f, "many_to_one", False)]
        if any(getattr(f, "related_model", None) is Cocktail for f in fks) and \
           any(getattr(f, "related_model", None) is Ingredient for f in fks):
            return m
    raise RuntimeError("No through model linking Cocktail and Ingredient found.")
Through = find_through_model()

# -------- locate Units model (db_table='units') anywhere --------
Unit = None
for m in apps.get_models():
    if m._meta.db_table == "units" or m.__name__ in ("Unit", "Units"):
        Unit = m
        break
if Unit is None:
    raise RuntimeError("Units model (db_table='units') not found.")

# ensure 'ml' unit exists (string PK or normal PK both OK)
ml_unit, _ = Unit.objects.get_or_create(name="ml")

def field_names(model):
    return {f.name for f in model._meta.get_fields()
            if getattr(f, "concrete", False) and not f.one_to_many and not f.many_to_many}

def first_existing(model, candidates):
    fns = field_names(model)
    for c in candidates:
        if c in fns:
            return c
    return None

cocktail_image_field   = first_existing(Cocktail,   ["image_url","photo_url","image","photo","picture_url","thumbnail","thumbnail_url"])
ingredient_image_field = first_existing(Ingredient, ["image_url","photo_url","image","photo","picture_url","thumbnail","thumbnail_url"])
amount_field           = first_existing(Through,    ["amount_ml","amount","quantity_ml","quantity","volume_ml","ml"])
is_garnish_field       = first_existing(Through,    ["is_garnish","garnish","is_optional"])

# detect unit FK field on through model
unit_candidates = ["unit_input","unit","input_unit","measure_unit"]
unit_field = first_existing(Through, unit_candidates)
unit_fk = getattr(Through, unit_field).field if unit_field else None
unit_targets_name = isinstance(unit_fk, ForeignKey) and getattr(unit_fk.target_field, "name", None) == "name"

# ---- NOT NULL defaults for Cocktail ----
def default_for_field(f):
    if f.has_default():
        try:
            return f.get_default()
        except Exception:
            pass
    if isinstance(f, (IntegerField, PositiveIntegerField, SmallIntegerField, PositiveSmallIntegerField)): return 0
    if isinstance(f, BooleanField): return False
    if isinstance(f, FloatField): return 0.0
    if isinstance(f, DecimalField): return Decimal("0")
    if isinstance(f, (CharField, TextField)): return ""
    if isinstance(f, DateTimeField): return timezone.now()
    if isinstance(f, DateField): return timezone.localdate()
    if isinstance(f, TimeField): return timezone.now().time()
    return None

def build_required_defaults_for_cocktail():
    required, missing = {}, []
    for f in Cocktail._meta.get_fields():
        if not getattr(f, "concrete", False) or f.auto_created: continue
        if f.name in ("id", "name"): continue
        if getattr(f, "null", True) is False and not f.has_default():
            if isinstance(f, ForeignKey):
                rel = f.remote_field.model
                obj = rel.objects.order_by("pk").first()
                if obj: required[f.name + "_id"] = obj.pk
                else:   missing.append(f"{f.name} -> {rel.__name__}")
            else:
                dv = default_for_field(f)
                if dv is None: missing.append(f"{f.name} (no default)")
                else:          required[f.name] = dv
    return required, missing

@transaction.atomic
def upsert_blow_job():
    # 1) ingredients
    def upsert_ing(name, url):
        obj, _ = Ingredient.objects.get_or_create(name=name)
        if ingredient_image_field and url:
            cur = getattr(obj, ingredient_image_field, None)
            if not cur or cur != url:
                setattr(obj, ingredient_image_field, url)
                obj.save(update_fields=[ingredient_image_field])
        return obj
    amaretto      = upsert_ing("Amaretto", INGR_IMG.get("Amaretto"))
    irish_cream   = upsert_ing("Irish Cream Liqueur", INGR_IMG.get("Irish Cream Liqueur"))
    whipped_cream = upsert_ing("Whipped Cream", INGR_IMG.get("Whipped Cream"))

    # 2) cocktail
    bj = Cocktail.objects.filter(name="Blow Job").first()
    if not bj:
        defaults, missing = build_required_defaults_for_cocktail()
        if cocktail_image_field: defaults[cocktail_image_field] = BLOW_JOB_IMG
        if missing:
            raise RuntimeError("Cannot auto-create Cocktail; required fields need values: " + ", ".join(missing))
        bj = Cocktail.objects.create(name="Blow Job", **defaults)
    else:
        if cocktail_image_field and getattr(bj, cocktail_image_field, None) != BLOW_JOB_IMG:
            setattr(bj, cocktail_image_field, BLOW_JOB_IMG)
            bj.save(update_fields=[cocktail_image_field])

    # 3) links (amount + garnish + unit='ml')
    def link(ing, amount_ml, garnish=False):
        kwargs = {"cocktail": bj, "ingredient": ing}
        defaults = {}
        if amount_field: defaults[amount_field] = Decimal(str(amount_ml))
        if is_garnish_field is not None: defaults[is_garnish_field] = bool(garnish)
        if unit_field:
            if unit_targets_name:
                # FK targets Units.name (string PK) → assign "<field>_id" to "ml"
                defaults[unit_field + "_id"] = "ml"
            else:
                defaults[unit_field] = ml_unit
        Through.objects.update_or_create(**kwargs, defaults=defaults)

    link(amaretto, 15, garnish=False)
    link(irish_cream, 15, garnish=False)
    link(whipped_cream, 5, garnish=True)

    return {"through_model": Through.__name__,
            "used_fields": {"amount_field": amount_field,
                            "is_garnish_field": is_garnish_field,
                            "unit_field": unit_field,
                            "unit_targets_name": unit_targets_name,
                            "cocktail_image_field": cocktail_image_field,
                            "ingredient_image_field": ingredient_image_field}}

info = upsert_blow_job()
print("✔ Blow Job added/updated. Field mapping:", info)
