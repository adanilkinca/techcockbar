from decimal import Decimal
from typing import Any, Dict, Iterable, Optional

from django.conf import settings
from django.contrib import admin
from django.db import transaction
from django.forms import ModelForm, ChoiceField, ValidationError
from django.utils.html import format_html

from .models import (
    Cocktail,
    Ingredient,
    CocktailIngredient,
    PricingSettings,
    # The three below may be managed=False views in your DB; they may or may not exist.
    # If any are missing, the defensive registration at the bottom will just skip them.
    CocktailPrice,
    CocktailAllergens,
    CocktailSummary,
)

from django.apps import apps
from decimal import Decimal, ROUND_HALF_UP

# --- units -> ounces
UNIT_TO_OZ = {
    "oz": Decimal("1"),
    "ml": Decimal("0.0333333333"),  # 1 ml ≈ 1/30 oz
    "dash": Decimal("0.03"),
    "leaf": Decimal("0"),
    "wedge": Decimal("0"),
}

def _dec(x, default="0"):
    if x is None:
        return Decimal(default)
    try:
        return Decimal(str(x))
    except Exception:
        return Decimal(default)

def _get_pricing_settings():
    from .models import PricingSettings
    try:
        return PricingSettings.objects.first()
    except Exception:
        return None

def _labor_cost(ps):
    for name in ("labor_cost_per_cocktail", "labor_per_cocktail", "labor_cost", "labor"):
        if ps and hasattr(ps, name):
            val = getattr(ps, name)
            if val is not None:
                return _dec(val, "0")
    return Decimal("0")

def _markup_multiplier(ps):
    if not ps:
        return Decimal("1")
    if hasattr(ps, "markup_multiplier") and ps.markup_multiplier is not None:
        return _dec(ps.markup_multiplier, "1")
    raw = None
    for name in ("default_markup", "markup", "markup_percent"):
        if hasattr(ps, name):
            raw = getattr(ps, name)
            if raw is not None:
                break
    m = _dec(raw, "0")
    if m > 1 and m > Decimal("2"):
        m = m / Decimal("100")
    return Decimal("1") + m

def _amount_oz(ci):
    """Prefer ci.amount_oz if present; else amount_input * unit_input."""
    amt_oz = _dec(getattr(ci, "amount_oz", None), None)
    if amt_oz is not None:
        return amt_oz
    amt_in = _dec(getattr(ci, "amount_input", None), "0")
    unit = (getattr(ci, "unit_input", "") or "oz").strip().lower()
    factor = UNIT_TO_OZ.get(unit, Decimal("1"))
    return (amt_in * factor)

# ---- Discover reverse accessor Cocktail -> CocktailIngredient dynamically
def _discover_ci_accessor():
    try:
        Through = apps.get_model("cocktails", "CocktailIngredient")
        fk = Through._meta.get_field("cocktail")
        return fk.remote_field.get_accessor_name()   # e.g., "cocktailingredient_set" or custom related_name
    except Exception:
        return None

_CI_ACCESSOR = _discover_ci_accessor()



# ----------------------------
# Helpers
# ----------------------------

def has_field(model, name: str) -> bool:
    """Return True if Django model has a concrete or proxy field named `name`."""
    try:
        return model._meta.get_field(name) is not None  # type: ignore[attr-defined]
    except Exception:
        return False


def get_attr(obj: Any, name: str, default: Any = None) -> Any:
    try:
        return getattr(obj, name)
    except Exception:
        return default


def set_if_has(obj: Any, name: str, value: Any) -> None:
    if has_field(obj.__class__, name):
        setattr(obj, name, value)


NOIMAGE_URL = getattr(settings, "NOIMAGE_URL",
                      "https://res.cloudinary.com/dau9qbp3l/image/upload/v1755145790/no-photo-master.png")

# ----------------------------
# Ingredient form (type dropdown) + previews
# ----------------------------

INGREDIENT_TYPES = [
    ("", "—"),
    ("spirit", "Spirits"),
    ("homemade", "Homemade"),
    ("vermouth", "Vermouth"),
    ("liqueur", "Liqueurs"),
    ("wine", "Wines"),
    ("beer_cider", "Beer and cider"),
    ("bitters", "Bitters"),
    ("syrup", "Syrups"),
    ("juice", "Juices"),
    ("soft_drink", "Water and soft drinks"),
    ("tea_coffee", "Tea and coffee"),
    ("dairy", "Dairy"),
    ("seafood", "Seafood"),
    ("puree", "Puree"),
    ("fruit", "Fruits"),
    ("berry", "Berries"),
    ("vegetable", "Vegetables"),
    ("plant", "Plants"),
    ("honey_jam", "Honey and jams"),
    ("sauce_oil", "Sauces and oil"),
    ("spice", "Spices"),
    ("nut_sweet", "Nuts and Sweet"),
]


class IngredientForm(ModelForm):
    # Make type a dropdown; if your DB column is short text, this still saves the raw key.
    type = ChoiceField(choices=INGREDIENT_TYPES, required=False)

    class Meta:
        model = Ingredient
        fields = ["name", "type", "abv_percent", "cost_per_oz", "is_housemade", "notes", "image_url"]

    # Normal form; preview is provided in admin's readonly field below.


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "type", "abv_percent", "cost_per_oz", "is_housemade", "image_thumb"]
    list_filter = ["type", "is_housemade"]
    search_fields = ["name"]
    form = IngredientForm

    # In the change form we show a preview with fallback, but in list_display we show a dash if empty.
    readonly_fields = ["image_preview"]

    fieldsets = (
        (None, {
            "fields": (
                "name",
                "type",
                ("abv_percent", "cost_per_oz"),
                "is_housemade",
                "notes",
                "image_url",
                "image_preview",
            )
        }),
    )

    def image_thumb(self, obj: Ingredient) -> str:
        url = get_attr(obj, "image_url") or ""
        if not url:
            return "—"
        return format_html('<img src="{}" style="height:24px;width:auto;border-radius:4px;" />', url)
    image_thumb.short_description = "Image"

    def image_preview(self, obj: Optional[Ingredient]) -> str:
        url = (getattr(obj, "image_url", "") or "").strip() if obj else ""
        if not url:
            url = NOIMAGE_URL
        return format_html('<img src="{}" style="height:120px;width:auto;border-radius:8px;" />', url)
    image_preview.short_description = "Preview"


# ----------------------------
# Inline for CocktailIngredient with unit dropdown
# ----------------------------

UNIT_CHOICES = [
    ("oz", "oz"),
    ("leaf", "leaf"),
    ("wedge", "wedge"),
    ("dash", "dash"),  # 0.03 oz
]

UNIT_TO_OZ = {
    "oz": Decimal("1"),
    "dash": Decimal("0.03"),
    "wedge": Decimal("0"),  # not counted toward fluid oz
    "leaf": Decimal("0"),   # not counted toward fluid oz
}


class CocktailIngredientInlineForm(ModelForm):
    unit_input = ChoiceField(choices=UNIT_CHOICES, required=False)

    class Meta:
        model = CocktailIngredient
        fields = "__all__"

    def clean(self):
        cleaned = super().clean()
        # Basic sanity: if amount_input provided, make sure it's numeric
        amt = cleaned.get("amount_input")
        if amt in ("", None):
            return cleaned
        try:
            Decimal(str(amt))
        except Exception as exc:
            raise ValidationError({"amount_input": f"Amount must be a number: {exc}"})
        return cleaned


class CocktailIngredientInline(admin.TabularInline):
    model = CocktailIngredient
    form = CocktailIngredientInlineForm
    extra = 0
    fields = ("seq", "ingredient", "amount_input", "unit_input", "amount_oz", "prep_note", "is_optional")
    readonly_fields = ("amount_oz",)
    ordering = ("seq",)

    def save_new_objects(self, formset, commit=True):
        objs = super().save_new_objects(formset, commit=False)
        self._convert_units(objs)
        if commit:
            for o in objs:
                o.save()
        return objs

    def save_existing_objects(self, formset, commit=True):
        objs, _ = super().save_existing_objects(formset, commit=False)
        self._convert_units(objs)
        if commit:
            for o in objs:
                o.save()
        return objs

    def _convert_units(self, objs: Iterable[CocktailIngredient]) -> None:
        for o in objs:
            unit = (o.unit_input or "").strip().lower()
            factor = UNIT_TO_OZ.get(unit, Decimal("1"))
            try:
                amt = Decimal(str(o.amount_input or 0))
            except Exception:
                amt = Decimal("0")
            o.amount_oz = amt * factor


# ----------------------------
# Cocktail admin with preview + recompute
# ----------------------------

class CocktailAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "status", "price_calc", "price_auto_safe", "cocktail_abv_safe", "image_thumb")
    list_filter = ("status",)
    search_fields = ("name",)
    inlines = [CocktailIngredientInline]
    readonly_fields = ("image_preview", "created_at_safe", "updated_at_safe")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if _CI_ACCESSOR:
            # prefetch through rows and their ingredient in one go
            return qs.prefetch_related(f"{_CI_ACCESSOR}__ingredient")
        return qs

    def price_calc(self, obj):
        """
        Price = (Σ(amount_oz * ingredient.cost_per_oz) + labor) * markup
        Falls back gracefully if something is missing.
        """
        total = Decimal("0")

        # Get the through rows from whatever the reverse accessor actually is
        rows = []
        if _CI_ACCESSOR and hasattr(obj, _CI_ACCESSOR):
            rows = getattr(obj, _CI_ACCESSOR).all()
        else:
            # last-resort common guesses
            for guess in ("cocktailingredient_set", "ci_rows", "rows"):
                if hasattr(obj, guess):
                    rows = getattr(obj, guess).all()
                    break

        for ci in rows:
            ing = getattr(ci, "ingredient", None)
            if not ing:
                continue
            amt_oz = _amount_oz(ci)
            cpo = _dec(getattr(ing, "cost_per_oz", None), "0")
            total += (amt_oz * cpo)

        ps = _get_pricing_settings()
        price = (total + _labor_cost(ps)) * _markup_multiplier(ps)

        if price <= 0:
            return self.admin_site.empty_value_display
        return f"{price.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)}"

    price_calc.short_description = "Price"

        

    # Prepopulate slug if the field exists
    def get_prepopulated_fields(self, request, obj=None):
        if has_field(Cocktail, "slug"):
            return {"slug": ("name",)}
        return {}

    # Layout tries to show common fields if they exist; missing ones are ignored by Django admin.
    fieldsets = (
        (None, {
            "fields": tuple(f for f in (
                "name",
                "slug" if has_field(Cocktail, "slug") else None,
                "short_story" if has_field(Cocktail, "short_story") else None,
                "story_long" if has_field(Cocktail, "story_long") else None,
                "image_url",
                "image_preview",
                "video_url" if has_field(Cocktail, "video_url") else None,
                "status" if has_field(Cocktail, "status") else None,
                "price_auto" if has_field(Cocktail, "price_auto") else None,
                "cocktail_abv" if has_field(Cocktail, "cocktail_abv") else None,
                "created_at_safe",
                "updated_at_safe",
            ) if f)
        }),
    )

    # --- list helpers
    def image_thumb(self, obj: Cocktail) -> str:
        url = get_attr(obj, "image_url") or ""
        if not url:
            return "—"
        return format_html('<img src="{}" style="height:24px;width:auto;border-radius:4px;" />', url)
    image_thumb.short_description = "Image"

    def price_auto_safe(self, obj: Cocktail) -> str:
        val = get_attr(obj, "price_auto")
        return f"{val:.3f}" if val is not None else "—"
    price_auto_safe.short_description = "Price"

    def cocktail_abv_safe(self, obj: Cocktail) -> str:
        val = get_attr(obj, "cocktail_abv")
        return f"{val:.2f}" if val is not None else "—"
    cocktail_abv_safe.short_description = "ABV %"

    # --- change form helpers
    def image_preview(self, obj: Optional[Cocktail]) -> str:
        url = (getattr(obj, "image_url", "") or "").strip() if obj else ""
        if not url:
            url = NOIMAGE_URL
        return format_html('<img src="{}" style="height:160px;width:auto;border-radius:8px;" />', url)
    image_preview.short_description = "Preview"

    def created_at_safe(self, obj: Optional[Cocktail]) -> str:
        return str(get_attr(obj, "created_at")) if obj and get_attr(obj, "created_at") else "—"
    created_at_safe.short_description = "Created at"

    def updated_at_safe(self, obj: Optional[Cocktail]) -> str:
        return str(get_attr(obj, "updated_at")) if obj and get_attr(obj, "updated_at") else "—"
    updated_at_safe.short_description = "Updated at"

    # --- recompute cocktail totals on save
    @transaction.atomic
    def save_formset(self, request, form, formset, change):
        objects = formset.save(commit=False)
        # Inlines handle unit conversion; just save and recalc below.
        for obj in objects:
            obj.save()
        for obj in formset.deleted_objects:
            obj.delete()
        self.recompute_totals(form.instance)

    @transaction.atomic
    def save_model(self, request, obj: Cocktail, form, change):
        super().save_model(request, obj, form, change)
        # Make sure totals are consistent if someone changed name/fields then saved without touching inlines
        self.recompute_totals(obj)

    # Price & ABV recompute (only touches fields if they exist)
    def recompute_totals(self, cocktail: Cocktail) -> None:
        # Sum ounces and cost
        qs = CocktailIngredient.objects.filter(cocktail=cocktail)
        total_oz = Decimal("0")
        total_cost = Decimal("0")
        abv_numer = Decimal("0")

        for row in qs.select_related("ingredient"):
            oz = Decimal(str(row.amount_oz or 0))
            total_oz += oz

            ing: Ingredient = row.ingredient
            cost_per_oz = Decimal(str(get_attr(ing, "cost_per_oz") or 0))
            total_cost += oz * cost_per_oz

            abv = Decimal(str(get_attr(ing, "abv_percent") or 0))  # % value like 40.00
            abv_numer += oz * (abv / Decimal("100"))

        # Pricing settings (optional)
        ps = PricingSettings.objects.first() if "PricingSettings" in globals() else None

        def pick_decimal(obj, names: Iterable[str], default: str = "0") -> Decimal:
            if not obj:
                return Decimal(default)
            for n in names:
                v = get_attr(obj, n)
                if v is not None:
                    try:
                        return Decimal(str(v))
                    except Exception:
                        pass
            return Decimal(default)

        labor = pick_decimal(
            ps,
            ["labor_per_cocktail", "labor_cost_per_cocktail", "labor_cost", "labor"],
            default="0",
        )
        total_cost += labor



# Register the cocktail admin
admin.site.register(Cocktail, CocktailAdmin)


# ----------------------------
# PricingSettings (simple, editable single-row table)
# ----------------------------

@admin.register(PricingSettings)
class PricingSettingsAdmin(admin.ModelAdmin):
    """
    Build list_display dynamically from whatever fields the PricingSettings model actually has.
    This avoids admin.E108 when field names differ (e.g., 'labor_cost' vs 'labor_per_cocktail').
    """
    def get_list_display(self, request):
        base = ["id"]
        ps_fields = {
            f.name
            for f in PricingSettings._meta.get_fields()
            if getattr(f, "concrete", False) and not getattr(f, "many_to_many", False)
        }
        # Show any of these that exist, in this order
        candidates = [
            "labor_per_cocktail",
            "labor_cost_per_cocktail",
            "labor_cost",
            "labor",
            "tax_pct",
            "overhead_pct",
            "margin_pct",
            "service_pct",
            "round_to",
        ]
        base.extend([name for name in candidates if name in ps_fields])
        return tuple(base)


# ----------------------------
# Read-only views: CocktailPrice, CocktailAllergens, CocktailSummary
# (Skip gracefully if a model is missing)
# ----------------------------

def register_readonly(model, list_display: Iterable[str], search: Iterable[str] = ()):
    """Register a simple read-only admin for a model if it exists."""
    if model is None:
        return

    class _RO(admin.ModelAdmin):  # type: ignore
        list_display = list(list_display)
        search_fields = list(search)
        actions = None

        def has_add_permission(self, request):  # noqa: N802
            return False

        def has_delete_permission(self, request, obj=None):  # noqa: N802
            return False

        def has_change_permission(self, request, obj=None):  # noqa: N802
            # We allow view (change page), but fields should be readonly by Model/DB (managed=False)
            return True

    try:
        admin.site.register(model, _RO)
    except admin.sites.AlreadyRegistered:
        pass


# Try to register these if the models exist in your codebase
try:
    register_readonly(CocktailPrice, ("cocktail", "price_raw", "price_rounded"), search=("cocktail__name",))
except Exception:
    pass

try:
    register_readonly(CocktailAllergens, ("cocktail", "allergens_json"), search=("cocktail__name",))
except Exception:
    pass

try:
    # Adapt to whatever fields exist in your CocktailSummary view
    summary_fields = []
    for cand in ("cocktail", "price", "abv", "ingredients_json", "tags_json"):
        if 'CocktailSummary' in globals() and has_field(CocktailSummary, cand):
            summary_fields.append(cand)
    if not summary_fields:
        summary_fields = ("cocktail",)
    register_readonly(CocktailSummary, summary_fields, search=("cocktail__name",))
except Exception:
    pass


# ----------------------------
# Admin site cosmetics
# ----------------------------

admin.site.site_header = "Cocktail Admin"
admin.site.site_title = "Cocktail Admin"
admin.site.index_title = "Cocktails"
