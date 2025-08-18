# cocktails/admin/cocktails.py
from django.contrib import admin
from django.utils.html import format_html
from django.conf import settings

from ..models import Cocktail, CocktailIngredient, CocktailSummary
from ..forms import CocktailIngredientInlineForm  # keeps the unit dropdown (oz, wedge, leaf, dash)

# Placeholder for previews only (list view still shows blank when image_url is missing)
PLACEHOLDER = getattr(
    settings,
    "NO_IMAGE_URL",
    "https://res.cloudinary.com/dau9qbp3l/image/upload/v1755145790/no-photo-master.png",
)


class CocktailIngredientInline(admin.TabularInline):
    model = CocktailIngredient
    form = CocktailIngredientInlineForm        # <-- important: binds the ChoiceField for unit_input
    extra = 0
    fields = ("seq", "ingredient", "amount_input", "unit_input", "amount_oz", "prep_note", "is_optional")
    readonly_fields = ("amount_oz",)
    ordering = ("seq",)


@admin.register(Cocktail)
class CocktailAdmin(admin.ModelAdmin):
    inlines = [CocktailIngredientInline]

    list_display = ("name", "status", "price_list", "abv_list", "image_icon")
    list_filter = ("status",)
    search_fields = ("name", "slug")
    ordering = ("id",)
    prepopulated_fields = {"slug": ("name",)}

    fieldsets = (
        (None, {"fields": ("name", "slug", "story_long")}),
        ("Media", {"fields": ("image_url", "image_preview", "video_url")}),
        ("Status & system", {"fields": ("status", "price_auto", "created_at", "updated_at")}),
    )
    readonly_fields = ("image_preview", "price_auto", "created_at", "updated_at")

    # -------- helpers --------
    def _summary(self, obj):
        try:
            return CocktailSummary.objects.only("abv_percent", "price_suggested").get(id=obj.id)
        except CocktailSummary.DoesNotExist:
            return None

    # -------- list columns --------
    @admin.display(description="Price")
    def price_list(self, obj):
        s = self._summary(obj)
        if not s or s.price_suggested is None:
            return "—"
        return f"{s.price_suggested:.2f}"

    @admin.display(description="ABV %")
    def abv_list(self, obj):
        s = self._summary(obj)
        if not s or s.abv_percent is None:
            return "—"
        return f"{s.abv_percent:.2f}"

    @admin.display(description="Image")
    def image_icon(self, obj):
        # Blank in list when missing so you can see which ones still need images
        if not obj.image_url:
            return "—"
        return format_html('<img src="{}" style="height:18px;width:auto;border-radius:3px;" />', obj.image_url)

    # -------- form read-only fields --------
    @admin.display(description="Preview")
    def image_preview(self, obj):
        url = obj.image_url or PLACEHOLDER
        return format_html('<img src="{}" style="height:120px;width:auto;border-radius:8px;" />', url)

    @admin.display(description="Price (auto)")
    def price_auto(self, obj):
        s = self._summary(obj)
        if not s or s.price_suggested is None:
            return "—"
        return f"{s.price_suggested:.3f}"
