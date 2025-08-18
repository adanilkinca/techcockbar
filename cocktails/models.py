from django.db import models

# --- Tables ---

class Tag(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    class Meta:
        managed = False
        db_table = "tags"
    def __str__(self): return self.name

# cocktails/models.py (Ingredient excerpt)
class Ingredient(models.Model):
    id = models.BigAutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    type = models.CharField(max_length=64, null=True, blank=True)  # category
    abv_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)  # e.g. 40.00
    cost_per_oz = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    is_housemade = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True)
    image_url = models.URLField(blank=True, null=True)
    class Meta:
        managed = False
        db_table = "ingredients"
    def __str__(self):
        return self.name


class Cocktail(models.Model):
    STATUS_CHOICES = (("draft","draft"),("published","published"),("archived","archived"))
    id = models.BigAutoField(primary_key=True)
    slug = models.CharField(max_length=140, unique=True)
    name = models.CharField(max_length=255)
    glass_type = models.CharField(max_length=80, null=True, blank=True)
    flavor_scale = models.PositiveSmallIntegerField(default=0)  # 1..10
    invention_year = models.SmallIntegerField(null=True, blank=True)
    description_short = models.TextField(null=True, blank=True)
    story_long = models.TextField(null=True, blank=True)
    time_to_make_sec = models.IntegerField(default=0)
    price_auto = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    image_url = models.CharField(max_length=500, null=True, blank=True)
    video_url = models.CharField(max_length=500, null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default="draft")
    created_at = models.DateTimeField(auto_now_add=False)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        managed = False
        db_table = "cocktails"
    def __str__(self): return self.name

class PricingSettings(models.Model):
    id = models.SmallIntegerField(primary_key=True)  # always 1
    labor_cost_per_hour = models.DecimalField(max_digits=10, decimal_places=2, default=20)
    overhead_pct = models.DecimalField(max_digits=6, decimal_places=4, default=0.10)
    price_round_increment = models.DecimalField(max_digits=6, decimal_places=3, default=0.25)
    class Meta:
        managed = False
        db_table = "settings"
    def __str__(self): return "Pricing Settings"

# --- Views ---

class CocktailABV(models.Model):
    cocktail = models.OneToOneField(Cocktail, primary_key=True,
                                    db_column="cocktail_id", on_delete=models.DO_NOTHING,
                                    related_name="abv_row")
    abv_percent = models.DecimalField(max_digits=5, decimal_places=2)
    class Meta:
        managed = False
        db_table = "cocktail_abv_v"

class CocktailPrice(models.Model):
    cocktail = models.OneToOneField(Cocktail, primary_key=True,
                                    db_column="cocktail_id", on_delete=models.DO_NOTHING,
                                    related_name="price_row")
    price_raw = models.DecimalField(max_digits=12, decimal_places=6)
    price_rounded = models.DecimalField(max_digits=12, decimal_places=3)
    class Meta:
        managed = False
        db_table = "cocktail_price_v"

class CocktailAllergens(models.Model):
    cocktail = models.OneToOneField(Cocktail, primary_key=True,
                                    db_column="cocktail_id", on_delete=models.DO_NOTHING,
                                    related_name="allergen_row")
    allergens_json = models.JSONField(null=True)
    class Meta:
        managed = False
        db_table = "cocktail_allergens_v"

class CocktailSummary(models.Model):
    id = models.BigIntegerField(primary_key=True)  # view exposes c.id as 'id'
    slug = models.CharField(max_length=140)
    name = models.CharField(max_length=255)
    glass_type = models.CharField(max_length=80, null=True)
    flavor_scale = models.PositiveSmallIntegerField()
    invention_year = models.SmallIntegerField(null=True)
    description_short = models.TextField(null=True)
    story_long = models.TextField(null=True)
    time_to_make_sec = models.IntegerField()
    abv_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    price_suggested = models.DecimalField(max_digits=12, decimal_places=3, null=True)
    allergens_json = models.JSONField(null=True)
    class Meta:
        managed = False
        db_table = "cocktail_summary_v"
    def __str__(self):
        # show a nice label in admin headers and dropdowns
        return f"{self.name} ({self.slug})" if self.name else f"Summary #{self.id}"


# Convenience props for admin display
def _cocktail_abv(self):
    try: return self.abv_row.abv_percent
    except CocktailABV.DoesNotExist: return None
def _cocktail_price(self):
    try: return self.price_row.price_rounded
    except CocktailPrice.DoesNotExist: return None
def _cocktail_allergens(self):
    try: return self.allergen_row.allergens_json
    except CocktailAllergens.DoesNotExist: return None

class Unit(models.Model):
    name = models.CharField(primary_key=True, max_length=32)
    to_oz_factor = models.DecimalField(max_digits=12, decimal_places=6, null=True)   # e.g. ml=1/30
    non_volumetric = models.BooleanField(default=False)
    oz_equivalent = models.DecimalField(max_digits=12, decimal_places=6, null=True)

    class Meta:
        managed = False
        db_table = "units"
    def __str__(self): return self.name


class CocktailIngredient(models.Model):
    # NOTE: we added this surrogate id in TiDB already
    id = models.BigAutoField(primary_key=True)
    cocktail = models.ForeignKey("Cocktail", on_delete=models.CASCADE,
                                 db_column="cocktail_id", related_name="lines")
    ingredient = models.ForeignKey("Ingredient", on_delete=models.PROTECT,
                                   db_column="ingredient_id")
    seq = models.SmallIntegerField(default=1)
    amount_oz = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    unit_input = models.CharField(max_length=32)
    amount_input = models.DecimalField(max_digits=10, decimal_places=4, default=0)
    prep_note = models.CharField(max_length=255, null=True, blank=True)
    is_optional = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = "cocktail_ingredients"
        unique_together = (("cocktail", "ingredient", "seq"),)

    def __str__(self):
        return f"{self.cocktail_id} · {self.ingredient_id} · {self.seq}"


Cocktail.cocktail_abv = property(_cocktail_abv)
Cocktail.cocktail_price = property(_cocktail_price)
Cocktail.cocktail_allergens = property(_cocktail_allergens)
