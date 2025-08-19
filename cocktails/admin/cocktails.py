# cocktails/admin/cocktails.py
from decimal import Decimal

from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import slugify
from django.utils import timezone

from ..models import Cocktail, CocktailIngredient, CocktailSummary
from ..forms import CocktailIngredientInlineForm


# --- helpers ---------------------------------------------------------------

def _to_oz(amount, unit):
    """
    Minimal conversion used in your earlier fixes:
      - 'oz' passes through
      - 'ml' converts to oz (1 oz = 29.5735 ml)
      - everything else -> 0 to avoid guessing
    Mirrors commit a8df4be logic.
    """
    if amount is None:
        return Decimal("0")
    unit = (unit or "").lower()
    amt = Decimal(str(amount))
    if unit == "oz":
        return amt
    if unit == "ml":
        return amt / Decimal("29.5735")
    return Decimal("0")


# --- inlines ---------------------------------------------------------------

class CocktailIngredientInline(admin.TabularInline):
    model = CocktailIngredient
    form = CocktailIngredientInlineForm
    extra = 0
    # Hide amount_oz in the form (exactly like your prior fix)
    fields = ("seq", "ingredient", "amount_input", "unit_input", "prep_note", "is_optional")
    ordering = ("seq",)
    verbose_name = "Cocktail ingredient"
    verbose_name_plural = "Cocktail ingredients"


# --- admin -----------------------------------------------------------------

@admin.register(Cocktail)
class CocktailAdmin(admin.ModelAdmin):
    inlines = [CocktailIngredientInline]

    list_display = ("name", "status", "price_column", "abv_column", "image_list")
    search_fields = ("name", "slug")
    ordering = ("name",)
    prepopulated_fields = {"slug": ("name",)}

    fieldsets = (
        ("Basics", {"fields": ("name", "slug", "story_long")}),
        ("Media", {"fields": ("image_url", "image_preview", "video_url")}),
        ("Status & system", {"fields": ("status", "glass_type", "price_auto", "created_at", "updated_at")}),
    )
    readonly_fields = ("image_preview", "price_auto", "created_at", "updated_at")

    # ---------- persistence hooks ----------
    def save_formset(self, request, form, formset, change):
        """
        **The key fix** from your prior commits:
        persist `amount_oz` for each inline so the SQL VIEW has fresh data.
        """
        instances = formset.save(commit=False)
        for obj in instances:
            obj.amount_oz = _to_oz(obj.amount_input, getattr(obj, "unit_input", None))
            obj.save()
        # handle deletes & m2m
        for obj in formset.deleted_objects:
            obj.delete()
        formset.save_m2m()

    def _ensure_unique_slug(self, base: str, *, instance_id=None) -> str:
        s = slugify(base) or "item"
        orig = s
        i = 2
        qs = Cocktail.objects.all()
        if instance_id:
            qs = qs.exclude(pk=instance_id)
        while qs.filter(slug=s).exists():
            s = f"{orig}-{i}"
            i += 1
        return s

    def save_model(self, request, obj, form, change):
        # Ensure slug and timestamps (kept from your code)
        if not obj.slug:
            obj.slug = self._ensure_unique_slug(obj.name, instance_id=obj.pk)
        now = timezone.now()
        if not obj.created_at:
            obj.created_at = now
        obj.updated_at = now
        super().save_model(request, obj, form, change)

    # ---------- UI helpers ----------
    @admin.display(description="Preview")
    def image_preview(self, obj: Cocktail):
        url = obj.image_url or ""
        return (
            format_html('<img src="{}" style="height:110px;width:auto;border-radius:6px;" />', url)
            if url else format_html('<div style="opacity:.5">No image</div>')
        )

    @admin.display(description="PRICE")
    def price_column(self, obj: Cocktail):
        # Read from the SQL view (same PK as Cocktail) – matches your earlier fix
        s = CocktailSummary.objects.filter(pk=obj.pk).only("price_suggested").first()
        return "—" if not s or s.price_suggested is None else f"{s.price_suggested:.2f}"

    @admin.display(description="ABV %")
    def abv_column(self, obj: Cocktail):
        s = CocktailSummary.objects.filter(pk=obj.pk).only("abv_percent").first()
        return "—" if not s or s.abv_percent is None else f"{s.abv_percent:.2f}"

    @admin.display(description="Price (auto)")
    def price_auto(self, obj: Cocktail):
        s = CocktailSummary.objects.filter(pk=obj.pk).only("price_suggested").first()
        return "—" if not s or s.price_suggested is None else f"{s.price_suggested:.2f}"

    @admin.display(description="IMAGE")
    def image_list(self, obj: Cocktail):
        return (
            format_html('<img src="{}" style="height:18px;width:auto;border-radius:3px;" />', obj.image_url)
            if obj.image_url else "—"
        )
