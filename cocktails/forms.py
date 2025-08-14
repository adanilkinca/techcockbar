from decimal import Decimal, ROUND_HALF_UP
from django import forms
from django.apps import apps

# -----------------------------
# Shared helpers
# -----------------------------

UNIT_CHOICES = (
    ("oz", "oz"),
    ("leaf", "leaf"),
    ("wedge", "wedge"),
    ("dash", "dash"),
)

INGREDIENT_TYPE_CHOICES = (
    ("spirit", "Spirits"),
    ("homemade", "Homemade"),
    ("vermouth", "Vermouth"),
    ("liqueur", "Liqueurs"),
    ("wine", "Wines"),
    ("beer", "Beer and cider"),
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
)

def _quantize_money(x: Decimal) -> Decimal:
    if x is None:
        return Decimal("0.00")
    return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

def compute_cocktail_cost(cocktail) -> Decimal:
    """
    Compute cost defensively: never rely on a particular related_name.
    """
    CocktailIngredient = apps.get_model("cocktails", "CocktailIngredient")
    PricingSettings = apps.get_model("cocktails", "PricingSettings")

    total = Decimal("0")
    rows = (
        CocktailIngredient.objects
        .filter(cocktail=cocktail)
        .select_related("ingredient")
        .only("amount_oz", "ingredient__cost_per_oz")
    )
    for r in rows:
        amt = r.amount_oz or Decimal("0")
        cpo = r.ingredient.cost_per_oz if r.ingredient else Decimal("0")
        total += (amt * cpo)

    ps = PricingSettings.objects.first()
    if ps is not None:
        labor = getattr(ps, "labor_cost_per_cocktail", None)
        if labor is None:
            labor = getattr(ps, "labor_per_cocktail", None)
        if labor:
            total += Decimal(labor)

    return _quantize_money(total)


# -----------------------------
# Forms
# -----------------------------

class IngredientAdminForm(forms.ModelForm):
    type = forms.ChoiceField(
        choices=(("", "—"),) + INGREDIENT_TYPE_CHOICES,
        required=False,
    )

    class Meta:
        model = apps.get_model("cocktails", "Ingredient")
        fields = "__all__"


class CocktailIngredientInlineForm(forms.ModelForm):
    unit_input = forms.ChoiceField(choices=UNIT_CHOICES, required=False)

    class Meta:
        model = apps.get_model("cocktails", "CocktailIngredient")
        fields = "__all__"


class CocktailAdminForm(forms.ModelForm):
    price_auto_display = forms.DecimalField(
        label="Price (auto)",
        required=False,
        disabled=True,
        decimal_places=2,
        max_digits=10,
        help_text="Calculated from ingredients + labor (read-only).",
    )

    class Meta:
        model = apps.get_model("cocktails", "Cocktail")
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        instance = kwargs.get("instance")
        if instance and instance.pk:
            self.fields["price_auto_display"].initial = compute_cocktail_cost(instance)
        else:
            self.fields["price_auto_display"].initial = Decimal("0.00")
