# cocktails/admin.py
from django.contrib import admin
from django import forms
from django.utils.html import format_html
from .models import Cocktail, Ingredient, CocktailIngredient, PricingSettings
from .utils.pricing import compute_totals, compute_price

# --- Inline form: restrict unit choices -------------------------------------
UNIT_CHOICES = (("oz", "oz"), ("leaf", "leaf"), ("wedge", "wedge"), ("dash", "dash"))

class CocktailIngredientInlineForm(forms.ModelForm):
    unit_input = forms.ChoiceField(choices=UNIT_CHOICES, required=False)
    class Meta:
        model = CocktailIngredient
        fields = "__all__"

class CocktailIngredientInline(admin.TabularInline):
    model = CocktailIngredient
    form = CocktailIngredientInlineForm
    extra = 0
    fields = ("seq", "ingredient", "amount_input", "unit_input", "amount_oz", "prep_note", "is_optional")
    readonly_fields = ("amount_oz",)
    ordering = ("seq",)

# --- Common tiny helpers -----------------------------------------------------
def _thumb(url, size=40):
    if not url:
        return ""
    return format_html('<img src="{}" width="{}" height="{}" style="object-fit:cover;border-radius:6px"/>',
                       url, size, size)

# --- Ingredient admin --------------------------------------------------------
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "type", "abv_percent", "cost_per_oz", "is_housemade", "image_icon")
    list_filter = ("type", "is_housemade")
    search_fields = ("name",)

    fields = ("name", "type", "abv_percent", "cost_per_oz", "is_housemade", "notes", "image_url")
    readonly_fields = ()

    def image_icon(self, obj):
        # show blank when missing so you can see what needs pictures
        return _thumb(getattr(obj, "image_url", None), 28)
    image_icon.short_description = "Image"
    image_icon.allow_tags = True

# --- Cocktail admin ----------------------------------------------------------
class CocktailAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "status", "price_admin", "abv_admin", "image_icon")
    list_filter = ("status",)
    search_fields = ("name", "slug")
    inlines = (CocktailIngredientInline,)

    fieldsets = (
        (None, {
            "fields": ("name", "slug", "story_long")
        }),
        ("Media", {
            "fields": ("image_url", "video_url", "preview_admin")
        }),
        ("Status & system", {
            "fields": ("status", "price_auto", "created_at", "updated_at")
        }),
    )
    readonly_fields = ("preview_admin", "created_at", "updated_at")

    # --- previews / list columns ---
    def preview_admin(self, obj):
        return _thumb(getattr(obj, "image_url", None), 120)
    preview_admin.short_description = "Preview"

    def image_icon(self, obj):
        return _thumb(getattr(obj, "image_url", None), 20)
    image_icon.short_description = "Image"

    def abv_admin(self, obj):
        # compute ABV% from ingredients (no DB view)
        _, abv, _ = compute_totals(obj)
        return f"{abv}"
    abv_admin.short_description = "ABV %"

    def price_admin(self, obj):
        try:
            return f"{compute_price(obj)}"
        except Exception:
            return "—"
    price_admin.short_description = "Price"

# --- Pricing settings admin --------------------------------------------------
class PricingSettingsAdmin(admin.ModelAdmin):
    # be tolerant to differing field names; show what exists
    list_display = []
    for name in ["labor_per_cocktail", "labor", "labor_cost",
                 "markup_percent", "markup",
                 "overhead_percent", "overhead"]:
        if hasattr(PricingSettings, name):
            list_display.append(name)
    if not list_display:
        list_display = ("id",)

# --- Register ---------------------------------------------------------------
admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Cocktail, CocktailAdmin)
admin.site.register(PricingSettings, PricingSettingsAdmin)
