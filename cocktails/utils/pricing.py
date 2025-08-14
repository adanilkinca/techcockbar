# cocktails/utils/pricing.py
from decimal import Decimal, ROUND_HALF_UP
from django.apps import apps

# Convert admin "unit_input" into ounces for cost/abv math
_UNIT_TO_OZ = {
    "oz": Decimal("1"),
    "dash": Decimal("0.03"),
    # leaf/wedge are garnish/non-liquid for our math; treat as 0 volume
    "leaf": Decimal("0"),
    "wedge": Decimal("0"),
}

def _to_decimal(val, default="0"):
    if val is None:
        return Decimal(default)
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal(default)

def _amount_to_oz(amount_input, unit_input):
    unit = (unit_input or "").lower()
    mult = _UNIT_TO_OZ.get(unit, Decimal("0"))
    return (_to_decimal(amount_input) * mult).quantize(Decimal("0.0001"))

def compute_totals(cocktail):
    """
    Returns: (total_volume_oz, abv_percent, ingredients_cost)
    """
    CocktailIngredient = apps.get_model("cocktails", "CocktailIngredient")
    rows = (CocktailIngredient.objects
            .filter(cocktail=cocktail)
            .select_related("ingredient"))

    total_oz = Decimal("0")
    pure_alcohol_oz = Decimal("0")
    ing_cost = Decimal("0")

    for r in rows:
        # Prefer explicit amount_oz if present; otherwise convert
        oz = _to_decimal(getattr(r, "amount_oz", None))
        if oz == 0:
            oz = _amount_to_oz(getattr(r, "amount_input", None),
                               getattr(r, "unit_input", ""))

        ing = r.ingredient
        abv = _to_decimal(getattr(ing, "abv_percent", None))
        cost_per_oz = _to_decimal(getattr(ing, "cost_per_oz", None))

        total_oz += oz
        pure_alcohol_oz += (oz * abv / Decimal("100"))
        ing_cost += (oz * cost_per_oz)

    abv_percent = (pure_alcohol_oz / total_oz * Decimal("100")) if total_oz else Decimal("0")
    abv_percent = abv_percent.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    ing_cost = ing_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return total_oz, abv_percent, ing_cost

def _get_ps_value(ps, *names, default="0"):
    for n in names:
        if hasattr(ps, n):
            return _to_decimal(getattr(ps, n), default)
    return Decimal(default)

def compute_price(cocktail):
    """
    price = (ingredients_cost + labor_flat) * (1 + (markup+overhead)/100)
    Field names are probed defensively to match your current model.
    """
    _, _, ingredients_cost = compute_totals(cocktail)

    PricingSettings = apps.get_model("cocktails", "PricingSettings")
    ps = PricingSettings.objects.first()  # ok for admin list

    labor = _get_ps_value(ps, "labor_per_cocktail", "labor", "labor_cost")
    markup = _get_ps_value(ps, "markup_percent", "markup")
    overhead = _get_ps_value(ps, "overhead_percent", "overhead")

    subtotal = ingredients_cost + labor
    factor = Decimal("1") + (markup + overhead) / Decimal("100")
    price = (subtotal * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return price
