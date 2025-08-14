from decimal import Decimal
from django import forms
from .models import Cocktail, CocktailIngredient, Ingredient

# ===== Admin UI choices =====
UNIT_CHOICES = [("oz", "oz"), ("leaf", "leaf"), ("wedge", "wedge"), ("dash", "dash")]

INGREDIENT_TYPE_CHOICES = [
    ("Spirits", "Spirits"),
    ("Homemade", "Homemade"),
    ("Vermouth", "Vermouth"),
    ("Liqueurs", "Liqueurs"),
    ("Wines", "Wines"),
    ("Beer and cider", "Beer and cider"),
    ("Bitters", "Bitters"),
    ("Syrups", "Syrups"),
    ("Juices", "Juices"),
    ("Water and soft drinks", "Water and soft drinks"),
    ("Tea and coffee", "Tea and coffee"),
    ("Dairy", "Dairy"),
    ("Seafood", "Seafood"),
    ("Puree", "Puree"),
    ("Fruits", "Fruits"),
    ("Berries", "Berries"),
    ("Vegetables", "Vegetables"),
    ("Plants", "Plants"),
    ("Honey and jams", "Honey and jams"),
    ("Sauces and oil", "Sauces and oil"),
    ("Spices", "Spices"),
    ("Nuts and Sweet", "Nuts and Sweet"),
]

def _has_field(model, name: str) -> bool:
    return any(getattr(f, "concrete", False) and f.name == name for f in model._meta.get_fields())

# ===== Cocktail inline (unchanged from earlier answer) =====
class CocktailIngredientInlineForm(forms.ModelForm):
    unit_input = forms.ChoiceField(choices=UNIT_CHOICES, initial="oz")

    class Meta:
        model = CocktailIngredient
        fields = "__all__"

    def save(self, commit=True):
        inst = super().save(commit=False)
        try:
            amt = self.cleaned_data.get("amount_input")
            unit = self.cleaned_data.get("unit_input") or getattr(inst, "unit_input", None)
            if amt is not None and hasattr(inst, "amount_oz"):
                if unit == "oz":
                    inst.amount_oz = amt
                elif unit == "dash":
                    inst.amount_oz = (amt or Decimal("0")) * Decimal("0.03")
                else:
                    inst.amount_oz = Decimal("0")
        except Exception:
            pass
        if commit:
            inst.save()
        return inst

class CocktailAdminForm(forms.ModelForm):
    class Meta:
        model = Cocktail
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "glass_type" in self.fields:
            # (optional nice dropdown if you added choices on the model)
            self.fields["glass_type"].required = False

# ===== Ingredient form (NEW) =====
class IngredientAdminForm(forms.ModelForm):
    """
    - Forces 'type' to be a dropdown with your fixed categories.
    - Exposes 'image_url' as a normal URL field (you'll add it on the model below).
    """
    # render 'type' as dropdown (even if the model is just a CharField)
    if _has_field(Ingredient, "type"):
        type = forms.ChoiceField(choices=INGREDIENT_TYPE_CHOICES, required=False)

    class Meta:
        model = Ingredient
        fields = "__all__"
