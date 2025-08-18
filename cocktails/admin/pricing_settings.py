from django.contrib import admin
from ..models import PricingSettings

@admin.register(PricingSettings)
class PricingSettingsAdmin(admin.ModelAdmin):
    """
    Keep this simple; the model defines the fields. We avoid custom list_display
    so it won’t break if the table shape changes.
    """
    pass
