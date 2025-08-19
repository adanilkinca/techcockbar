from decimal import Decimal
from django.contrib import admin
from cocktails.models import CocktailSummary


@admin.register(CocktailSummary)
class CocktailSummaryAdmin(admin.ModelAdmin):
    list_display = ("name", "abv_percent_display", "price_suggested_display")

    @admin.display(description="ABV percent")
    def abv_percent_display(self, obj):
        return f"{Decimal(obj.abv_percent):.2f}" if obj.abv_percent is not None else "—"

    @admin.display(description="Price suggested")
    def price_suggested_display(self, obj):
        return f"{Decimal(obj.price_suggested):.2f}" if obj.price_suggested is not None else "—"
