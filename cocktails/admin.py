from decimal import Decimal

from django.conf import settings
from django.contrib import admin
from django.db import models
from django.utils.html import format_html

from .forms import (
    CocktailIngredientInlineForm,
    IngredientAdminForm,
)
from .models import (
    Cocktail,
    CocktailIngredient,
    Ingredient,
    PricingSettings,
    CocktailSummary,
)

# --- pricing helpers ---------------------------------------------------------

# We rely on your small utils module for all math.
# If names change in the future this won't crash admin.
PRICE_FN = None
ABV_FN = None
try:
    from utils.pricing import compute_cocktail_price, compute_cocktail_abv  # preferred names

    PRICE_FN = compute_cocktail_price
    ABV_FN = compute_cocktail_abv
except Exception:
    try:
        from utils.pricing import price_for_cocktail as PRICE_FN  # legacy name
    except Exception:
        PRICE_FN = None
    try:
        from utils.pricing import abv_for_cocktail as ABV_FN  # legacy name
    except Exception:
        ABV_FN = None


def safe_price(cocktail: Cocktail):
    if PRICE_FN is None:
        return None
    try:
        val = PRICE_FN(cocktail)
        return Decimal(val) if val is not None else None
    except Exception:
        return None


def safe_abv(cocktail: Cocktail):
    if ABV_FN is None:
        return None
    try:
        val = ABV_FN(cocktail)
        return Decimal(val) if val is not None else None
    except Exception:
        return None


# --- inlines -----------------------------------------------------------------

class CocktailIngredientInline(admin.TabularInline):
    model = CocktailIngredient
    form = CocktailIngredientInlineForm
    extra = 0
    fields = ("seq", "ingredient", "amount_input", "unit_input", "amount_oz", "prep_note", "is_optional")
    readonly_fields = ("amount_oz",)
    ordering = ("seq",)


# --- mixins ------------------------------------------------------------------

NO_IMAGE_URL = getattr(
    settings,
    "ADMIN_DEFAULT_IMAGE_URL",
    "https://res.cloudinary.com/dau9qbp3l/image/upload/v1755145790/no-photo-master.png",
)


class PreviewMixin:
    """Show a small preview in change form; in lists we keep '-' if empty."""

    image_url_field_name = "image_url"

    def _obj_image_url(self, obj):
        url = getattr(obj, self.image_url_field_name, None)
        return url or NO_IMAGE_URL

    @admin.display(description="Preview")
    def image_preview(self, obj):
        url = self._obj_image_url(obj)
        return format_html('<img src="{}" style="height:90px;border-radius:8px;">', url)

    @admin.display(description="Image")
    def image_thumb_or_dash(self, obj):
        """Use dash in lists if there is no image_url (so you can see what’s missing)."""
        url = getattr(obj, self.image_url_field_name, None)
        if not url:
            return "—"
        return format_html('<img src="{}" style="height:24px;">', url)


# --- Cocktail admin -----------------------------------------------------------

@admin.register(Cocktail)
class CocktailAdmin(PreviewMixin, admin.ModelAdmin):
    list_display = ("name", "status", "price_list", "abv_list", "image_thumb_or_dash")
    list_filter = ("status",)
    search_fields = ("name", "slug")
    readonly_fields = ("image_preview", "price_auto", "abv_auto", "created_at", "updated_at")
    inlines = [CocktailIngredientInline]

    fieldsets = (
        (None, {"fields": ("name", "slug", "story_long")}),
        ("Media", {"fields": ("image_url", "image_preview", "video_url")}),
        ("Status & system", {"fields": ("status", "price_auto", "abv_auto", "created_at", "updated_at")}),
    )

    # --- readonly values in the form
    @admin.display(description="Price (auto)")
    def price_auto(self, obj):
        val = safe_price(obj)
        return f"{val:.2f}" if val is not None else "—"

    @admin.display(description="ABV (auto)")
    def abv_auto(self, obj):
        val = safe_abv(obj)
        return f"{val:.2f}" if val is not None else "—"

    # --- columns in the list
    @admin.display(description="Price")
    def price_list(self, obj):
        val = safe_price(obj)
        return f"{val:.2f}" if val is not None else "—"

    @admin.display(description="ABV %")
    def abv_list(self, obj):
        val = safe_abv(obj)
        return f"{val:.2f}" if val is not None else "—"


# --- Ingredient admin --------------------------------------------------------

@admin.register(Ingredient)
class IngredientAdmin(PreviewMixin, admin.ModelAdmin):
    form = IngredientAdminForm
    list_display = ("id", "name", "type", "abv_percent", "cost_per_oz", "is_housemade", "image_thumb_or_dash")
    list_filter = ("type", "is_housemade")
    search_fields = ("name",)
    readonly_fields = ("image_preview",)
    fields = ("name", "type", "abv_percent", "cost_per_oz", "is_housemade", "notes", "image_url", "image_preview")


# --- Cocktail summary (read-only) --------------------------------------------

@admin.register(CocktailSummary)
class CocktailSummaryAdmin(admin.ModelAdmin):
    """Display-only rollup. We compute price with utils and show cocktail name safely."""

    list_display = ("cocktail_name", "abv_auto", "price_auto")
    search_fields = ("cocktail__name",)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Cocktail")
    def cocktail_name(self, obj):
        # Works whether model has FK or an integer id
        ck = getattr(obj, "cocktail", None)
        if isinstance(ck, Cocktail):
            return ck.name
        # integer id or None
        cid = ck if isinstance(ck, int) else getattr(obj, "id", None)
        try:
            return Cocktail.objects.only("name").get(pk=cid).name
        except Exception:
            return "—"

    @admin.display(description="Price")
    def price_auto(self, obj):
        # Get a real cocktail instance for pricing
        ck = getattr(obj, "cocktail", None)
        cocktail = ck if isinstance(ck, Cocktail) else Cocktail.objects.filter(pk=getattr(obj, "id", None)).first()
        if not cocktail:
            return "—"
        val = safe_price(cocktail)
        return f"{val:.2f}" if val is not None else "—"

    @admin.display(description="ABV %")
    def abv_auto(self, obj):
        ck = getattr(obj, "cocktail", None)
        cocktail = ck if isinstance(ck, Cocktail) else Cocktail.objects.filter(pk=getattr(obj, "id", None)).first()
        if not cocktail:
            return "—"
        val = safe_abv(cocktail)
        return f"{val:.2f}" if val is not None else "—"


# --- Pricing settings admin (robust to field names) --------------------------

@admin.register(PricingSettings)
class PricingSettingsAdmin(admin.ModelAdmin):
    """Minimal & resilient; avoids referencing non-existing field names."""

    def get_list_display(self, request):
        # Show whatever the model really has, in a stable order.
        names = [f.name for f in PricingSettings._meta.fields if f.editable]
        if "id" in names:
            names.remove("id")
            names = ["id"] + names
        return names

    search_fields = tuple(f.name for f in PricingSettings._meta.fields if isinstance(f, (models.CharField,)))
