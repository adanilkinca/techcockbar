from django import forms
from .models import Ingredient, CocktailIngredient

# --- Ingredient admin form: force a clean, fixed set of types via dropdown ---
INGREDIENT_TYPE_CHOICES = [
    ("spirit", "Spirits"),
    ("homemade", "Homemade"),
    ("vermouth", "Vermouth"),
    ("liqueur", "Liqueurs"),
    ("wine", "Wines"),
    ("beer_cider", "Beer and cider"),
    ("bitters", "Bitters"),
    ("syrup", "Syrups"),
    ("juice", "Juices"),
    ("soft_drink", "Water and soft drinks"),
    ("tea_coffee", "Tea and coffee"),
    ("dairy", "Dairy"),
    ("seafood", "Seafood"),
    ("puree", "Puree"),
    ("fruit", "Fruits"),
    ("berry", "Berries"),
    ("vegetable", "Vegetables"),
    ("plant", "Plants"),
    ("honey_jam", "Honey and jams"),
    ("sauce_oil", "Sauces and oil"),
    ("spice", "Spices"),
    ("nuts_sweet", "Nuts and Sweet"),
]

class IngredientAdminForm(forms.ModelForm):
    # Ingredient.type is a CharField in DB; expose a dropdown here.
    type = forms.ChoiceField(choices=[("", "—")] + INGREDIENT_TYPE_CHOICES, required=False)

    class Meta:
        model = Ingredient
        fields = "__all__"

# --- Cocktail ingredient inline: unit dropdown (oz/leaf/wedge/dash) ---
UNIT_CHOICES = [
    ("oz", "oz"),
    ("leaf", "leaf"),
    ("wedge", "wedge"),
    ("dash", "dash"),  # ≈ 0.03 oz (conversion handled by DB logic / existing code)
]

class CocktailIngredientInlineForm(forms.ModelForm):
    unit_input = forms.ChoiceField(choices=UNIT_CHOICES, required=False)

    class Meta:
        model = CocktailIngredient
        fields = "__all__"
