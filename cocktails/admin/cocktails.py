# cocktails/admin/cocktails.py
from django.contrib import admin
from django.utils.html import format_html
from django.utils.text import slugify
from django.utils import timezone
from django.conf import settings
from .metrics import compute_price_and_abv

from ..models import Cocktail, CocktailIngredient, CocktailSummary
from ..forms import CocktailIngredientInlineForm

# Fallback placeholder if settings.NO_IMAGE_URL is not defined
PLACEHOLDER = getattr(
    settings,
    "NO_IMAGE_URL",
    "https://res.cloudinary.com/dau9qbp3l/image/upload/v1755145790/no-photo-master.png",
)


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

    # ------------------- persistence helpers -------------------

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
        # Guarantee a slug even if JS didn't run
        if not obj.slug:
            obj.slug = self._ensure_unique_slug(obj.name, instance_id=obj.pk)

        # DB safety: never allow NULL flavor_scale (MySQL strict)
        if getattr(obj, "flavor_scale", None) is None:
            obj.flavor_scale = 0

        # DB requires created_at NOT NULL; bump updated_at on every save
        now = timezone.now()
        if not obj.created_at:
            obj.created_at = now
        obj.updated_at = now

        super().save_model(request, obj, form, change)
        
        # ——— Computed columns: price & ABV ———
    def price_column(self, obj):
        price, _ = compute_price_and_abv(obj)
        return f"{price:.2f}"
    price_column.short_description = "Price"

    def abv_column(self, obj):
        _, abv = compute_price_and_abv(obj)
        return f"{abv:.2f}"
    abv_column.short_description = "ABV %"

    # (Optional) show it inside the form as read-only – keep your existing fields, just add this name:
    def price_auto(self, obj):
        if not obj or not obj.pk:
            return "-"
        price, _ = compute_price_and_abv(obj)
        return f"{price:.2f}"
    price_auto.short_description = "Price (auto)"


    # ------------------- UI helpers -------------------

    @admin.display(description="Preview")
    def image_preview(self, obj: Cocktail):
        url = obj.image_url or PLACEHOLDER
        return format_html('<img src="{}" style="height:110px;width:auto;border-radius:6px;" />', url)

    @admin.display(description="Price (auto)")
    def price_auto(self, obj: Cocktail):
        s = CocktailSummary.objects.filter(id=obj.pk).only("price_suggested").first()
        return "—" if not s or s.price_suggested is None else f"{s.price_suggested:.2f}"

    @admin.display(description="PRICE")
    def price_column(self, obj: Cocktail):
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
