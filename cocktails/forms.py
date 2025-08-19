# cocktails/forms.py
from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError

from .models import Ingredient, CocktailIngredient


def _unit_choices():
    """
    Pull choices from the model in one place.
    Works with TextChoices (Unit.choices) or legacy UNIT_CHOICES.
    """
    unit_enum = getattr(CocktailIngredient, "Unit", None)
    if unit_enum and hasattr(unit_enum, "choices"):
        return list(unit_enum.choices)

    legacy = getattr(CocktailIngredient, "UNIT_CHOICES", None)
    if legacy:
        return list(legacy)

    # Fallback so admin never breaks (will be overwritten by real choices in model)
    return [("oz", "oz"), ("ml", "ml")]


class IngredientAdminForm(forms.ModelForm):
    class Meta:
        model = Ingredient
        fields = [
            "name",
            "type",
            "abv_percent",
            "cost_per_oz",
            "is_housemade",
            "notes",
            "image_url",
        ]


class CocktailIngredientInlineForm(forms.ModelForm):
    """
    Critical: keep unit_input a ChoiceField (dropdown), not a text box.
    """
    unit_input = forms.ChoiceField(
        choices=_unit_choices(),
        required=True,
        label="Unit input",
    )

    class Meta:
        model = CocktailIngredient
        fields = [
            "seq",
            "ingredient",
            "amount_input",
            "unit_input",
            "prep_note",
            "is_optional",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["amount_input"].widget.attrs.setdefault("style", "width:120px")

        # Edit case: show current value
        if getattr(self.instance, "unit_input", None):
            self.fields["unit_input"].initial = self.instance.unit_input
            return

        # Optional default from Ingredient if your model exposes it
        ing: Ingredient | None = (
            self.instance.ingredient
            if getattr(self.instance, "ingredient_id", None)
            else None
        )
        default_from_ing = getattr(ing, "default_unit", None)
        if default_from_ing:
            valid = {c[0] for c in self.fields["unit_input"].choices}
            if default_from_ing in valid:
                self.fields["unit_input"].initial = default_from_ing

    def clean_unit_input(self):
        val = self.cleaned_data.get("unit_input")
        valid = {c[0] for c in self.fields["unit_input"].choices}
        if val not in valid:
            raise ValidationError("Select a valid unit.")
        return val
