# cocktails/admin/cocktail_summaries.py
from django import forms
from django.contrib import admin

from ..models import CocktailSummary


def _is_choices_like(value) -> bool:
    if not isinstance(value, (list, tuple)) or not value:
        return False
    first = value[0]
    return isinstance(first, (list, tuple)) and len(first) == 2

def _resolve_glass_choices():
    try:
        from .. import constants as _c  # type: ignore
        for name in (
            "GLASS_CHOICES",
            "GLASS_TYPE_CHOICES",
            "GLASS_TYPES",
            "GLASSES",
            "GLASS",
        ):
            if hasattr(_c, name):
                val = getattr(_c, name)
                if _is_choices_like(val):
                    return list(val)
        for name in dir(_c):
            up = name.upper()
            if "GLASS" in up and ("CHOICE" in up or "TYPE" in up or "TYPES" in up):
                val = getattr(_c, name)
                if _is_choices_like(val):
                    return list(val)
    except Exception:
        pass

    try:
        field = CocktailSummary._meta.get_field("glass_type")
        if getattr(field, "choices", None):
            return list(field.choices)
    except Exception:
        pass
    return []

GLASS_CHOICES_RESOLVED = _resolve_glass_choices()


class CocktailSummaryAdminForm(forms.ModelForm):
    glass_type = forms.ChoiceField(
        choices=GLASS_CHOICES_RESOLVED,
        required=False,
        label="Glass type",
    )

    class Meta:
        model = CocktailSummary
        fields = [
            "name",
            "slug",
            "description_short",
            "flavor_scale",
            "glass_type",
            "invention_year",
            "price_suggested",
            "abv_percent",
            "story_long",
            "time_to_make_sec",
            "allergens_json",
        ]


@admin.register(CocktailSummary)
class CocktailSummaryAdmin(admin.ModelAdmin):
    form = CocktailSummaryAdminForm
    list_display = ("name", "price_suggested", "abv_percent", "glass_type")
    search_fields = ("name", "slug")
    ordering = ("name",)
