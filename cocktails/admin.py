from decimal import Decimal

from django import forms
from django.contrib import admin
from django.utils.safestring import mark_safe

from .models import (
    Cocktail,
    Ingredient,
    CocktailIngredient,
    PricingSettings,
    CocktailSummary,
    Tag,
    Unit,
)

# ============================================================
# Ingredient admin
# ============================================================

INGREDIENT_TYPE_CHOICES = (
    ("spirit", "Spirits"),
    ("housemade", "Homemade"),
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
    ("nuts_sweet", "Nuts and Sweet"),
)


class IngredientAdminForm(forms.ModelForm):
    # Force a dropdown in admin regardless of DB type
    type = forms.ChoiceField(choices=INGREDIENT_TYPE_CHOICES, required=False)

    class Meta:
        model = Ingredient
        fields = (
            "name",
            "type",
            "abv_percent",
            "cost_per_oz",
            "is_housemade",
            "image_url",
            "notes",
        )


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    form = IngredientAdminForm

    list_display = (
        "id",
        "name",
        "type",
        "abv_percent",
        "cost_per_oz",
        "is_housemade",
        "image_thumb",
    )
    list_filter = ("type", "is_housemade")
    search_fields = ("name",)
    readonly_fields = ("id", "image_preview")

    fieldsets = (
        ("Core", {"fields": ("id", "name", "type", "abv_percent", "cost_per_oz", "is_housemade")}),
        ("Image", {"fields": ("image_url", "image_preview")}),
        ("Notes", {"fields": ("notes",)}),
    )

    # ---- image helpers
    def image_preview(self, obj):
        url = getattr(obj, "image_url", None)
        if not url:
            return mark_safe('<div style="color:#999;">No image</div>')
        return mark_safe(f'<img src="{url}" style="max-width:220px;border-radius:8px;" />')

    image_preview.short_description = "Preview"

    def image_thumb(self, obj):
        url = getattr(obj, "image_url", None)
        return mark_safe(f'<img src="{url}" style="height:36px;border-radius:6px;" />') if url else "—"

    image_thumb.short_description = "Image"


# ============================================================
# Cocktail + Ingredients inline (unit limited to oz/leaf/wedge/dash)
# ============================================================

UNIT_CHOICES = (("oz", "oz"), ("leaf", "leaf"), ("wedge", "wedge"), ("dash", "dash"))


class CocktailIngredientInlineForm(forms.ModelForm):
    unit_input = forms.ChoiceField(choices=UNIT_CHOICES, required=False)

    class Meta:
        model = CocktailIngredient
        fields = (
            "seq",
            "ingredient",
            "amount_input",
            "unit_input",
            "prep_note",
            "is_optional",
        )


class CocktailIngredientInline(admin.TabularInline):
    model = CocktailIngredient
    form = CocktailIngredientInlineForm
    extra = 0
    fields = ("seq", "ingredient", "amount_input", "unit_input", "prep_note", "is_optional", "amount_oz_display")
    readonly_fields = ("amount_oz_display",)
    ordering = ("seq",)

    def amount_oz_display(self, obj):
        val = getattr(obj, "amount_oz", None)
        if isinstance(val, (int, float, Decimal)):
            return f"{Decimal(val):.4f}"
        return "—" if val is None else str(val)

    amount_oz_display.short_description = "Amount oz"


# Auto-populate slug from name, only if the field exists
_HAS_SLUG = any(getattr(f, "name", None) == "slug" and getattr(f, "concrete", False) for f in Cocktail._meta.get_fields())


@admin.register(Cocktail)
class CocktailAdmin(admin.ModelAdmin):
    inlines = [CocktailIngredientInline]
    search_fields = ("name",)
    list_display = ("id", "name", "status_safe", "image_thumb")
    list_filter = ("status",) if any(getattr(f, "name", None) == "status" for f in Cocktail._meta.get_fields()) else ()
    readonly_fields = ("image_preview",)

    if _HAS_SLUG:
        prepopulated_fields = {"slug": ("name",)}

    # ---- image helpers
    def image_preview(self, obj):
        url = getattr(obj, "image_url", None)
        if not url:
            return mark_safe('<div style="color:#999;">No image</div>')
        return mark_safe(f'<img src="{url}" style="max-width:260px;border-radius:10px;" />')

    image_preview.short_description = "Preview"

    def image_thumb(self, obj):
        url = getattr(obj, "image_url", None)
        return mark_safe(f'<img src="{url}" style="height:36px;border-radius:6px;" />') if url else "—"

    image_thumb.short_description = "Image"

    def status_safe(self, obj):
        return getattr(obj, "status", "—")

    status_safe.short_description = "Status"


# ============================================================
# Summaries (read-only) & Pricing
# ============================================================

@admin.register(CocktailSummary)
class CocktailSummaryAdmin(admin.ModelAdmin):
    """
    Read-only admin for the summary view/table. We don't hard-code columns:
    list display is built from whatever concrete fields exist.
    """

    def get_list_display(self, request):
        # concrete, non-M2M, non-reverse fields
        fields = [
            f.name
            for f in CocktailSummary._meta.get_fields()
            if getattr(f, "concrete", False) and not f.many_to_many and not f.one_to_many
        ]
        if not fields:
            return ("__str__",)

        cols = []
        # prefer these if present
        for pref in ("cocktail", "id", "name", "status", "price_auto", "abv"):
            if pref in fields and pref not in cols:
                cols.append(pref)
        # fill up with a few more to make it useful
        for f in fields:
            if f not in cols:
                cols.append(f)
            if len(cols) >= 5:
                break
        return tuple(cols)

    def has_add_permission(self, request):  # summaries come from DB logic
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PricingSettings)
class PricingSettingsAdmin(admin.ModelAdmin):
    """
    Global pricing/labor multipliers, etc. We don't hard-code fields so
    whatever exists in your model/table will render automatically.
    """
    pass


# Optional helpers
@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("id", "name")


@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = ("name", "to_oz") if hasattr(Unit, "to_oz") else ("name",)
