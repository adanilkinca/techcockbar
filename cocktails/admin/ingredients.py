from django.contrib import admin
from django.utils.html import format_html
from django.conf import settings
from ..models import Ingredient
from ..forms import IngredientAdminForm

# Use settings.NO_IMAGE_URL if present; otherwise fall back to your Cloudinary URL
PLACEHOLDER = getattr(
    settings,
    "NO_IMAGE_URL",
    "https://res.cloudinary.com/dau9qbp3l/image/upload/v1755145790/no-photo-master.png",
)

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    form = IngredientAdminForm

    list_display = ("id", "name", "type", "abv_percent", "cost_per_oz", "is_housemade", "image_thumb")
    list_filter = ("type", "is_housemade")
    search_fields = ("name",)
    ordering = ("id",)

    fieldsets = (
        (None, {
            "fields": ("name", "type", "abv_percent", "cost_per_oz", "is_housemade")
        }),
        ("Notes", {
            "fields": ("notes",),
        }),
        ("Media", {
            "fields": ("image_url", "image_preview"),
        }),
    )
    readonly_fields = ("image_preview",)

    @admin.display(description="Image")
    def image_thumb(self, obj):
        # Keep list blank for missing images so you can see what's not set
        if not obj.image_url:
            return "—"
        return format_html(
            '<img src="{}" style="height:22px;width:auto;border-radius:4px;" />',
            obj.image_url,
        )

    @admin.display(description="Preview")
    def image_preview(self, obj):
        url = obj.image_url or PLACEHOLDER
        return format_html(
            '<img src="{}" style="height:120px;width:auto;border-radius:8px;" />',
            url,
        )
