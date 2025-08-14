from decimal import Decimal
from django.contrib import admin
from django.utils.html import format_html
from django.apps import apps

from .forms import (
    IngredientAdminForm,
    CocktailIngredientInlineForm,
    CocktailAdminForm,
    compute_cocktail_cost,
)

# Models
Cocktail = apps.get_model("cocktails", "Cocktail")
Ingredient = apps.get_model("cocktails", "Ingredient")
CocktailIngredient = apps.get_model("cocktails", "CocktailIngredient")
PricingSettings = apps.get_model("cocktails", "PricingSettings")
CocktailSummary = apps.get_model("cocktails", "CocktailSummary")

# -------------------------------------------------
# helpers
# -------------------------------------------------

def cloudinary_thumb(url: str, size=64) -> str:
    if not url or "res.cloudinary.com" not in url:
        return url or ""
    return url.replace("/upload/", f"/upload/c_fill,g_auto,h_{size},w_{size},q_auto,f_auto/", 1)

# -------------------------------------------------
# INLINES
# -------------------------------------------------

class CocktailIngredientInline(admin.TabularInline):
    model = CocktailIngredient
    form = CocktailIngredientInlineForm
    extra = 0
    fields = (
        "seq",
        "ingredient",
        "amount_input",
        "unit_input",
        "amount_oz",
        "prep_note",
        "is_optional",
    )
    readonly_fields = ("amount_oz",)
    ordering = ("seq",)

# -------------------------------------------------
# INGREDIENT ADMIN
# -------------------------------------------------

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
        "image_col",
    )
    list_filter = ("type", "is_housemade")
    search_fields = ("name",)
    readonly_fields = ("image_preview",)

    fieldsets = (
        (None, {
            "fields": ("name", "type", "abv_percent", "cost_per_oz", "is_housemade", "notes"),
        }),
        ("Media", {
            "fields": ("image_url", "image_preview"),
        }),
    )

    def image_col(self, obj):
        if not obj.image_url:
            return "—"
        return format_html(
            '<img src="{}" width="24" height="24" style="border-radius:4px;object-fit:cover;" />',
            cloudinary_thumb(obj.image_url, 24),
        )
    image_col.short_description = "Image"

    def image_preview(self, obj):
        if not obj.image_url:
            return "—"
        return format_html(
            '<img src="{}" width="96" height="96" style="border-radius:8px;object-fit:cover;" />',
            cloudinary_thumb(obj.image_url, 96),
        )
    image_preview.short_description = "Preview"

# -------------------------------------------------
# COCKTAIL ADMIN
# -------------------------------------------------

@admin.register(Cocktail)
class CocktailAdmin(admin.ModelAdmin):
    form = CocktailAdminForm
    inlines = [CocktailIngredientInline]

    list_display = ("id", "name", "status", "price_admin", "abv_admin", "image_col")
    list_filter = ("status",)
    search_fields = ("name", "slug")
    readonly_fields = ("image_preview", "created_at", "updated_at", "price_auto_readonly")

    fieldsets = (
        (None, {
            "fields": ("name", "slug", "story_long"),
        }),
        ("Media", {
            "fields": ("image_url", "image_preview", "video_url"),
        }),
        ("Status & system", {
            "fields": ("status", "price_auto_readonly", "created_at", "updated_at"),
        }),
    )

    # list columns

    def price_admin(self, obj):
        val = compute_cocktail_cost(obj)
        return f"{val:.2f}"
    price_admin.short_description = "Price"

    def abv_admin(self, obj):
        # Try to read from summary if available
        try:
            if hasattr(obj, "summary") and getattr(obj, "summary", None):
                pct = getattr(obj.summary, "abv_percent", None)
            else:
                summary = CocktailSummary.objects.filter(cocktail=obj).only("abv_percent").first()
                pct = summary.abv_percent if summary else None
            return f"{pct:.2f}" if pct is not None else "—"
        except Exception:
            return "—"
    abv_admin.short_description = "ABV %"

    def image_col(self, obj):
        url = getattr(obj, "image_url", "") or ""
        if not url:
            return "—"
        return format_html(
            '<img src="{}" width="24" height="24" style="border-radius:4px;object-fit:cover;" />',
            cloudinary_thumb(url, 24),
        )
    image_col.short_description = "Image"

    # readonly widgets shown on the form

    def image_preview(self, obj):
        url = getattr(obj, "image_url", "") or ""
        if not url:
            return "—"
        return format_html(
            '<img src="{}" width="96" height="96" style="border-radius:8px;object-fit:cover;" />',
            cloudinary_thumb(url, 96),
        )
    image_preview.short_description = "Preview"

    def price_auto_readonly(self, obj):
        if not obj or not getattr(obj, "pk", None):
            return "—"
        val = compute_cocktail_cost(obj)
        return format_html("<strong>{:.2f}</strong>", val)
    price_auto_readonly.short_description = "Price (auto)"

# -------------------------------------------------
# PRICING SETTINGS ADMIN
# -------------------------------------------------

@admin.register(PricingSettings)
class PricingSettingsAdmin(admin.ModelAdmin):
    def labor_display(self, obj):
        val = getattr(obj, "labor_cost_per_cocktail", None)
        if val is None:
            val = getattr(obj, "labor_per_cocktail", None)
        return f"{Decimal(val):.2f}" if val is not None else "—"
    labor_display.short_description = "Labor per cocktail"

    list_display = ("id", "labor_display")
    # Leave the form simple; whichever of the two fields exists will render.
    fields = ("labor_cost_per_cocktail",)

# -------------------------------------------------
# COCKTAIL SUMMARY (read-only, resilient to schema)
# -------------------------------------------------

@admin.register(CocktailSummary)
class CocktailSummaryAdmin(admin.ModelAdmin):
    """
    Read-only viewer that adapts to whichever columns your summary view exposes.
    """
    list_display = ("display_cocktail", "abv_col", "price_col")
    search_fields = ("cocktail__name",)

    # hard-disable CRUD
    def has_add_permission(self, request): return False
    def has_change_permission(self, request, obj=None): return False
    def has_delete_permission(self, request, obj=None): return False

    # columns that tolerate missing fields
    def display_cocktail(self, obj):
        c = getattr(obj, "cocktail", None)
        return c if c is not None else "—"
    display_cocktail.short_description = "Cocktail"

    def abv_col(self, obj):
        pct = getattr(obj, "abv_percent", None)
        try:
            return f"{pct:.2f}" if pct is not None else "—"
        except Exception:
            return "—"
    abv_col.short_description = "ABV %"

    def price_col(self, obj):
        # Prefer summary-provided prices if present; otherwise compute
        for attr in ("price_rounded", "price_raw", "price"):
            val = getattr(obj, attr, None)
            if val is not None:
                try:
                    return f"{Decimal(val):.2f}"
                except Exception:
                    return str(val)
        c = getattr(obj, "cocktail", None)
        if c is not None:
            try:
                return f"{compute_cocktail_cost(c):.2f}"
            except Exception:
                pass
        return "—"
    price_col.short_description = "Price"
