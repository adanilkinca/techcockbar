# cocktails/admin/ingredients.py
from django import forms
from django.contrib import admin
from django.utils.html import format_html

from ..models import Ingredient
from ..forms import IngredientAdminForm


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    form = IngredientAdminForm

    # Changelist columns (no "is_housemade")
    list_display = ("id", "name", "type", "abv_percent", "cost_per_oz_2dp", "image_column")
    list_display_links = ("id", "name")
    search_fields = ("name",)

    # ✅ bring back the filter by ingredient type
    list_filter = ("type",)

    ordering = ("id",)

    # --- form field tweak: force 2dp + step on the edit page ---
    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "cost_per_oz":
            kwargs["form_class"] = forms.DecimalField
            kwargs["decimal_places"] = 2
            kwargs["max_digits"] = getattr(db_field, "max_digits", 12)
            field = db_field.formfield(**kwargs)
            if field and hasattr(field, "widget"):
                field.widget.attrs.update({"step": "0.01"})
            return field
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    @admin.display(description="COST PER OZ")
    def cost_per_oz_2dp(self, obj: Ingredient):
        v = getattr(obj, "cost_per_oz", None)
        return "" if v is None else f"{float(v):.2f}"

    @admin.display(description="IMAGE")
    def image_column(self, obj: Ingredient):
        return (
            format_html('<img src="{}" style="height:18px;width:auto;border-radius:3px;" />', obj.image_url)
            if obj.image_url else "—"
        )
