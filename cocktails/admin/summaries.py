from django.contrib import admin
from ..models import CocktailSummary

@admin.register(CocktailSummary)
class CocktailSummaryAdmin(admin.ModelAdmin):
    """
    Read-only view of the DB summary (unmanaged model or DB view).
    """
    list_display = ("name", "abv_percent", "price_suggested")
    search_fields = ("name", "slug")
    ordering = ("id",)

    # show everything as read-only
    def has_add_permission(self, request):   # no create
        return False

    def has_change_permission(self, request, obj=None):  # detail page is view-only
        # Allow opening the detail page but don't allow edits (Django still needs change perms for the page).
        return True

    def save_model(self, request, obj, form, change):    # block saving
        return

    def delete_model(self, request, obj):                # block deleting from admin
        return
