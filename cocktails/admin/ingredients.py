from django.contrib import admin
from django.utils.html import format_html
from ..models import Ingredient
from ..forms import IngredientAdminForm

NO_IMAGE = None  # we intentionally show blank in lists if missing

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
        if not obj.image_url:
            return "—"
        return format_html('<img src="{}" style="height:22px;width:auto;border-radius:4px;" />', obj.image_url)

    @admin.display(description="Preview")
    def image_preview(self, obj):
        if not obj.image_url:
            return format_html('<div style="opacity:.5">No image</div>')
        return format_html('<img src="{}" style="height:120px;width:auto;border-radius:8px;" />', obj.image_url)
