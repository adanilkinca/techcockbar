from decimal import Decimal

from django.conf import settings
from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import slugify
from django.utils import timezone

from ..models import Cocktail, CocktailIngredient, CocktailSummary
from ..forms import CocktailIngredientInlineForm

# Fallback placeholder if settings.NO_IMAGE_URL is not defined
PLACEHOLDER = getattr(
    settings,
    "NO_IMAGE_URL",
    "https://res.cloudinary.com/dau9qbp3l/image/upload/v1755145790/no-photo-master.png",
)


# --- helpers -----------------------------------------------------------------

def _to_oz(amount, unit):
    """
    Minimal, conservative conversion to ounces for admin-side persistence.
    Only 'oz' is guaranteed in your current data; 'ml' included for convenience.
    Everything else returns 0 so we never guess wrong.
    """
    if amount is None:
        return Decimal("0")
    unit = (unit or "").lower()
    amt = Decimal(str(amount))
    if unit == "oz":
        return amt
    if unit == "ml":
        # 1 oz = 29.5735 ml
        return amt / Decimal("29.5735")
    # Unknown units -> don't try to infer
    return Decimal("0")


# --- inlines -----------------------------------------------------------------

class CocktailIngredientInline(admin.TabularInline):
    model = CocktailIngredient
    form = CocktailIngredientInlineForm
    extra = 0
    # Hide amount_oz from the form; keep your unit dropdown intact
    fields = (
        "seq",
        "ingredient",
        "amount_input",
        "unit_input",
        "prep_note",
        "is_optional",
    )
    ordering = ("seq",)
    # keep the row compact
    verbose_name = "Cocktail ingredient"
    verbose_name_plural = "Cocktail ingredients"


# --- admin -------------------------------------------------------------------

@admin.register(Cocktail)
class CocktailAdmin(admin.ModelAdmin):
    inlines = [CocktailIngredientInline]

    # Auto-fill slug from name in the admin UI
    prepopulated_fields = {"slug": ("name",)}

    # We do NOT show flavor_scale here (edited later in summaries)
    fieldsets = (
        ("", {"fields": ("name", "slug", "story_long")}),
        ("Media", {"fields": ("image_url", "image_preview", "video_url")}),
        ("Status & system", {"fields": ("status", "price_auto", "created_at", "updated_at")}),
    )
    readonly_fields = ("image_preview", "price_auto", "created_at", "updated_at")

    list_display = ("name", "status", "price_column", "abv_column", "image_list")
    search_fields = ("name", "slug")
    ordering = ("name",)

    # ---------- persistence hooks ----------

    def save_formset(self, request, form, formset, change):
        """
        Persist amount_oz for each inline so the SQL view (CocktailSummary)
        immediately has the data it needs for price/ABV.
        """
        instances = formset.save(commit=False)

        for obj in instances:
            # Convert input + unit → ounces and store in amount_oz
            obj.amount_oz = _to_oz(obj.amount_input, getattr(obj, "unit_input", None))
            obj.save()

        # Handle deletes & m2m
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()

    def _ensure_unique_slug(self, base: str, *, instance_id=None) -> str:
        """
        Make a unique slug from `base`. If a cocktail with the same slug exists,
        append -2, -3, ... until it's unique.
        """
        s = slugify(base) or "item"
        original = s
        i = 2
        while True:
            qs = Cocktail.objects.filter(slug=s)
            if instance_id:
                qs = qs.exclude(pk=instance_id)
            if not qs.exists():
                return s
            s = f"{original}-{i}"
            i += 1

    def save_model(self, request, obj, form, change):
        # Safety: guarantee slug even if client-side JS didn’t run
        if not obj.slug:
            obj.slug = self._ensure_unique_slug(obj.name, instance_id=obj.pk)

        # Safety: created/updated timestamps
        now = timezone.now()
        if not obj.created_at:
            obj.created_at = now
        obj.updated_at = now

        super().save_model(request, obj, form, change)

    # ---------- UI helpers ----------

    @admin.display(description="Preview")
    def image_preview(self, obj: Cocktail):
        url = obj.image_url or PLACEHOLDER
        return format_html('<img src="{}" style="height:110px;width:auto;border-radius:6px;" />', url)

    @admin.display(description="PRICE")
    def price_column(self, obj: Cocktail):
        # Read from your SQL view so values match the summaries section
        s = CocktailSummary.objects.filter(id=obj.pk).only("price_suggested").first()
        return "—" if not s or s.price_suggested is None else f"{s.price_suggested:.2f}"

    @admin.display(description="ABV %")
    def abv_column(self, obj: Cocktail):
        s = CocktailSummary.objects.filter(id=obj.pk).only("abv_percent").first()
        return "—" if not s or s.abv_percent is None else f"{s.abv_percent:.2f}"

    @admin.display(description="IMAGE")
    def image_list(self, obj: Cocktail):
        return (
            "—"
            if not obj.image_url
            else format_html('<img src="{}" style="height:18px;width:auto;border-radius:3px;" />', obj.image_url)
        )

    @admin.display(description="Price (auto)")
    def price_auto(self, obj: Cocktail):
        s = CocktailSummary.objects.filter(id=obj.pk).only("price_suggested").first()
        return "—" if not s or s.price_suggested is None else f"{s.price_suggested:.2f}"
