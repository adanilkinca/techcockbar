# cocktails/admin/metrics.py
from decimal import Decimal, ROUND_HALF_UP

OZ_PER_ML = Decimal("0.0338140227")

def _to_decimal(v):
    try:
        return Decimal(str(v))
    except Exception:
        return Decimal("0")

def _to_oz(amount_input, unit_input, amount_oz_db):
    """
    Use the saved amount_oz if it's positive; otherwise convert from the user input.
    We only normalize a couple of units (oz, ml). Everything else falls back to raw value.
    This keeps behavior identical to your current forms and avoids touching the unit UI.
    """
    amt_oz = _to_decimal(amount_oz_db)
    if amt_oz > 0:
        return amt_oz

    amt_in = _to_decimal(amount_input)
    unit = (unit_input or "").lower()

    if unit in ("oz", "ounce", "ounces"):
        return amt_in
    if unit == "ml":
        return (amt_in * OZ_PER_ML)

    # Fallback: treat as already-in-oz; this preserves current behavior for custom units.
    return amt_in

def compute_price_and_abv(cocktail):
    """
    Compute (price, abv_percent) from the current DB state for a Cocktail object.
    Works even immediately after creation, without relying on DB views or cached columns.
    """
    total_oz = Decimal("0")
    pure_alc_oz = Decimal("0")
    total_cost = Decimal("0")

    # Avoid circular import at module import time
    from cocktails.models import CocktailIngredient

    qs = (
        CocktailIngredient.objects
        .select_related("ingredient")
        .filter(cocktail_id=cocktail.pk)
    )

    for ci in qs:
        oz = _to_oz(ci.amount_input, ci.unit_input, ci.amount_oz)
        if oz <= 0:
            continue

        total_oz += oz

        ing = ci.ingredient
        if ing:
            # ABV
            abv = _to_decimal(getattr(ing, "abv_percent", 0))
            if abv > 0:
                pure_alc_oz += oz * (abv / Decimal("100"))

            # Cost
            cpo = _to_decimal(getattr(ing, "cost_per_oz", 0))
            if cpo > 0:
                total_cost += oz * cpo

    abv_pct = Decimal("0") if total_oz == 0 else (pure_alc_oz / total_oz * Decimal("100"))
    # Round for display, not storage
    total_cost = total_cost.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    abv_pct = abv_pct.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    return total_cost, abv_pct
