from django import forms

from .models import CocktailIngredient, Ingredient

# Units shown in admin only (data still stored as string in DB)
UNIT_CHOICES = [
    ("oz", "oz"),
    ("leaf", "leaf"),
    ("wedge", "wedge"),
    ("dash", "dash"),
]

# Optional: a tiny, safe guard so "type" is always one of our choices
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


class CocktailIngredientInlineForm(forms.ModelForm):
    unit_input = forms.ChoiceField(choices=UNIT_CHOICES, required=False)

    class Meta:
        model = CocktailIngredient
        fields = "__all__"


class IngredientAdminForm(forms.ModelForm):
    # keep free text in DB, but in admin show dropdown for consistency
    type = forms.ChoiceField(
        required=False,
        choices=[("", "—")] + INGREDIENT_TYPE_CHOICES,
    )

    class Meta:
        model = Ingredient
        fields = "__all__"
