from django.contrib import admin
from django.db import connection
from .models import (
    Cocktail, Ingredient, Tag, PricingSettings, CocktailSummary,
    CocktailIngredient, Unit
)
from .forms import CocktailIngredientInlineFormSet

UNIT_CHOICES = [("oz","oz"), ("leaf","leaf"), ("wedge","wedge"), ("dash","dash"), ("slice","slice")]

class CocktailIngredientInlineForm(forms.ModelForm):
    unit_input = forms.ChoiceField(choices=UNIT_CHOICES)

    class Meta:
        model = CocktailIngredient
        fields = "__all__"

class CocktailIngredientInline(admin.TabularInline):
    model = CocktailIngredient
    form = CocktailIngredientInlineForm
    extra = 0

class CocktailIngredientInline(admin.TabularInline):
    model = CocktailIngredient
    formset = CocktailIngredientInlineFormSet
    extra = 1
    fields = ("seq", "ingredient", "amount_input", "unit_input", "amount_oz", "prep_note", "is_optional")
    readonly_fields = ("amount_oz",)
    ordering = ("seq",)

    # Auto-convert amount_input + unit_input -> amount_oz (1oz = 30ml; units table drives it)
    def save_new_objects(self, formset, commit=True):
        objs = super().save_new_objects(formset, commit=False)
        self._convert_units(objs)
        if commit:
            for o in objs: o.save()
        return objs

    def save_existing_objects(self, formset, commit=True):
        (new, changed, deleted, formset_deleted) = super().save_existing_objects(formset, commit=False)
        self._convert_units(changed)
        if commit:
            for o in changed: o.save()
        return (new, changed, deleted, formset_deleted)

    def _convert_units(self, objs):
        # Pull all units once (name -> factors)
        units = {u.name: u for u in Unit.objects.all()}
        for o in objs:
            u = units.get(o.unit_input)
            if not u:  # unknown unit; leave as-is
                continue
            if u.non_volumetric:
                # e.g., leaf/slice/pinch — multiply oz_equivalent by the count
                o.amount_oz = (o.amount_input or 0) * (u.oz_equivalent or 0)
            else:
                # volumetric — multiply input by to_oz_factor
                o.amount_oz = (o.amount_input or 0) * (u.to_oz_factor or 0)


@admin.register(Cocktail)
class CocktailAdmin(admin.ModelAdmin):
    inlines = [CocktailIngredientInline]
    list_display = ("name", "slug", "glass_type", "flavor_scale", "cocktail_abv", "cocktail_price", "status")
    search_fields = ("name", "slug")
    list_filter = ("status",)
    readonly_fields = ("cocktail_abv", "cocktail_price", "cocktail_allergens")
    fields = (
        "slug", "name", "status",
        "glass_type", "flavor_scale", "invention_year",
        "description_short", "story_long",
        "time_to_make_sec", "image_url", "video_url",
        "cocktail_abv", "cocktail_price", "cocktail_allergens",
    )


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ("name",)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "abv_percent", "cost_per_oz", "is_housemade")
    search_fields = ("name",)
    list_filter = ("type", "is_housemade")


@admin.register(PricingSettings)
class PricingSettingsAdmin(admin.ModelAdmin):
    list_display = ("labor_cost_per_hour", "overhead_pct", "price_round_increment")
    def has_add_permission(self, request):  # single row table
        return False


@admin.register(CocktailSummary)
class CocktailSummaryAdmin(admin.ModelAdmin):
    list_display = ("name", "glass_type", "flavor_scale", "abv_percent", "price_suggested")
    search_fields = ("name", "slug")
    readonly_fields = tuple(f.name for f in CocktailSummary._meta.fields)
