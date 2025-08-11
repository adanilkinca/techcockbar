from django.contrib import admin
from django.utils.html import format_html
from .models import Cocktail, Ingredient, CocktailIngredient
from .forms import CocktailIngredientInlineForm, CocktailAdminForm

def _has_field(model, name: str) -> bool:
    return any(getattr(f, "concrete", False) and f.name == name for f in model._meta.get_fields())

class CocktailIngredientInline(admin.TabularInline):
    model = CocktailIngredient
    form = CocktailIngredientInlineForm
    extra = 0

    def get_fields(self, request, obj=None):
        wanted = ["seq", "ingredient", "amount_input", "unit_input", "amount_oz", "prep_note", "is_optional"]
        return [f for f in wanted if _has_field(self.model, f)]

    def get_readonly_fields(self, request, obj=None):
        ro = []
        if _has_field(self.model, "amount_oz"):
            ro.append("amount_oz")
        return ro

    def get_ordering(self, request):
        return ("seq",) if _has_field(self.model, "seq") else None


@admin.register(Cocktail)
class CocktailAdmin(admin.ModelAdmin):
    form = CocktailAdminForm
    inlines = [CocktailIngredientInline]
    readonly_fields = ("image_preview",)

    # Prepopulate slug from name, but only if both fields exist
    def get_prepopulated_fields(self, request, obj=None):
        if _has_field(Cocktail, "slug") and _has_field(Cocktail, "name"):
            return {"slug": ("name",)}
        return {}

    def image_preview(self, obj):
        # Try common image fields; show a small preview if present
        url = getattr(obj, "image_url", None) or getattr(obj, "photo_url", None)
        if url:
            return format_html('<img src="{}" style="max-width:240px;height:auto;border-radius:8px;" />', url)
        return "—"
    image_preview.short_description = "Preview"


# (Optional) Register Ingredient for convenience; safe no-op if already registered elsewhere
@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    search_fields = ("name",)
