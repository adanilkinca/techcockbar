# cocktails/admin/cocktail_summaries.py
from django import forms
from django.contrib import admin, messages

from ..models import CocktailSummary, Cocktail


# ---- glass choices resolver (constants-first, robust autodetect, model fallback)
def _is_choices_like(value) -> bool:
    if not isinstance(value, (list, tuple)) or not value:
        return False
    first = value[0]
    return isinstance(first, (list, tuple)) and len(first) == 2

def _resolve_glass_choices():
    # 1) constants.py with common names and shape check
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
    # 2) fallback to model field choices
    try:
        field = CocktailSummary._meta.get_field("glass_type")
        if getattr(field, "choices", None):
            return list(field.choices)
    except Exception:
        pass
    return []

GLASS_CHOICES_RESOLVED = _resolve_glass_choices()


class CocktailSummaryAdminForm(forms.ModelForm):
    """
    Editable form with all fields optional.
    Ensures Price suggested renders with EXACTLY 2 decimals.
    """
    glass_type = forms.ChoiceField(
        choices=GLASS_CHOICES_RESOLVED,
        required=False,
        label="Glass type",
    )
    price_suggested = forms.DecimalField(
        required=False,
        decimal_places=2,   # <-- 2dp in the form
        max_digits=12,
        label="Price suggested",
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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make every field non-required so Save works even when empty
        for f in self.fields.values():
            f.required = False

        # Force 2-decimal display and step on the widget
        if "price_suggested" in self.fields:
            self.fields["price_suggested"].widget.attrs.update({"step": "0.01"})
            v = getattr(self.instance, "price_suggested", None)
            if v is not None:
                try:
                    self.initial["price_suggested"] = f"{float(v):.2f}"
                except Exception:
                    pass


@admin.register(CocktailSummary)
class CocktailSummaryAdmin(admin.ModelAdmin):
    """
    Summary admin remains editable. Save will NOT write to the view (non-updatable);
    instead we proxy allowed fields to the upstream Cocktail row.
    Currently proxied: glass_type.
    """
    form = CocktailSummaryAdminForm

    list_display = ("name", "price_suggested_2dp", "abv_percent", "glass_type")
    search_fields = ("name", "slug")
    ordering = ("name",)

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

    @admin.display(description="PRICE SUGGESTED")
    def price_suggested_2dp(self, obj: CocktailSummary):
        v = getattr(obj, "price_suggested", None)
        return "" if v is None else f"{float(v):.2f}"

    def save_model(self, request, obj, form, change):
        """
        DO NOT save CocktailSummary (it's a DB VIEW).
        Proxy editable field(s) to Cocktail and show a success banner.
        """
        glass_val = form.cleaned_data.get("glass_type", None)

        # Update the upstream Cocktail (same PK as summary)
        try:
            cock = Cocktail.objects.get(pk=obj.pk)
            cock.glass_type = glass_val or None
            cock.save(update_fields=["glass_type"])
            messages.success(request, "Glass type updated on Cocktail.")
        except Cocktail.DoesNotExist:
            messages.error(request, "Linked Cocktail not found; cannot update glass type.")

        # Never call super().save_model(...) — avoids UPDATE on VIEW
        messages.success(
            request,
            "Saved changes to the form. Values shown here come from a database view; "
            "edit the Cocktail to persist other fields."
        )

    def has_add_permission(self, request):
        # Avoid creating rows for a view
        return False

    def has_delete_permission(self, request, obj=None):
        return False
