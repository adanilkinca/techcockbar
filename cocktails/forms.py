from decimal import Decimal
from django import forms
from .models import Cocktail, CocktailIngredient

# Admin UI choices
UNIT_CHOICES = [("oz", "oz"), ("leaf", "leaf"), ("wedge", "wedge"), ("dash", "dash")]

GLASS_CHOICES = [
    ("Shot", "Shot"), ("Hurricane", "Hurricane"), ("Sling", "Sling"), ("Rocks", "Rocks"),
    ("Highball", "Highball"), ("Goblet", "Goblet"), ("Cognac", "Cognac"), ("Pint", "Pint"),
    ("Collins", "Collins"), ("Cocktail", "Cocktail"), ("Red wine", "Red wine"),
    ("Margarita", "Margarita"), ("Irish coffee", "Irish coffee"),
    ("Milkshake", "Milkshake"), ("Tiki mug", "Tiki mug"), ("Jar", "Jar"),
]

def _has_field(model, name: str) -> bool:
    return any(getattr(f, "concrete", False) and f.name == name for f in model._meta.get_fields())

class CocktailIngredientInlineForm(forms.ModelForm):
    # Force the CharField to be one of the allowed units (your DB FK targets units.name)
    unit_input = forms.ChoiceField(choices=UNIT_CHOICES, initial="oz")

    class Meta:
        model = CocktailIngredient
        fields = "__all__"

    def save(self, commit=True):
        """
        If the through model has an 'amount_oz' field, keep it in sync with
        amount_input + unit_input. We assume:
          - oz   => 1.0
          - dash => 0.03 oz
          - leaf/wedge => non-fluid (store 0.0 oz)
        """
        inst = super().save(commit=False)

        try:
            amt = self.cleaned_data.get("amount_input")
            unit = self.cleaned_data.get("unit_input") or getattr(inst, "unit_input", None)

            if amt is not None and hasattr(inst, "amount_oz"):
                if unit == "oz":
                    inst.amount_oz = amt
                elif unit == "dash":
                    inst.amount_oz = (amt or Decimal("0")) * Decimal("0.03")
                else:  # leaf / wedge / anything non-fluid
                    inst.amount_oz = Decimal("0")
        except Exception:
            # never block admin save on a conversion hiccup
            pass

        if commit:
            inst.save()
        return inst


class CocktailAdminForm(forms.ModelForm):
    """
    Uses a curated dropdown for glass type *if* that field exists.
    (If your model doesn’t have 'glass_type', nothing special happens.)
    """
    class Meta:
        model = Cocktail
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "glass_type" in self.fields:
            self.fields["glass_type"] = forms.ChoiceField(
                choices=GLASS_CHOICES,
                initial=getattr(self.instance, "glass_type", None),
                required=False,
            )
