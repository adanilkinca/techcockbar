from django.contrib import admin
from ..models import CocktailSummary


@admin.register(CocktailSummary)
class CocktailSummaryAdmin(admin.ModelAdmin):
    # Keep name sortable; show ABV; format price to 2 decimals
    list_display = ("name", "abv_percent", "price_column")
    search_fields = ("name", "slug")
    ordering = ("name",)

    # Show the detail page as read-only (nice for viewing)
    readonly_fields = tuple(f.name for f in CocktailSummary._meta.fields)

    @admin.display(ordering="price_suggested", description="Price suggested")
    def price_column(self, obj: CocktailSummary):
        return "—" if obj.price_suggested is None else f"{obj.price_suggested:.2f}"
