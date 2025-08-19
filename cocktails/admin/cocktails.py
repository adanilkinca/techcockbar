from decimal import Decimal
from django import forms
from django.contrib import admin
from django.db import connection
from django.utils.safestring import mark_safe

from cocktails.models import Cocktail, CocktailIngredient


# Inline (kept exactly like your working version: oz stays readonly)
class CocktailIngredientInline(admin.TabularInline):
    model = CocktailIngredient
    extra = 0
    fields = ("seq", "ingredient", "amount_input", "unit_input", "amount_oz", "prep_note")
    readonly_fields = ("amount_oz",)
    ordering = ("seq",)


# Dropdown choices for glass type (extend anytime)
GLASS_TYPE_CHOICES = [
    ("Highball", "Highball"),
    ("Rocks", "Rocks / Old Fashioned"),
    ("Shot", "Shot"),
    ("Martini", "Martini / Cocktail"),
    ("Hurricane", "Hurricane"),
    ("Margarita", "Margarita"),
    ("Coupe", "Coupe / Champagne Saucer"),
    ("Collins", "Collins"),
    ("Flute", "Flute"),
    ("Irish Coffee", "Irish Coffee"),
    ("Red Wine", "Red Wine / Wine"),
    ("White Wine", "White Wine / Bowl / Orb"),
    ("Nick & Nora", "Nick & Nora"),
    ("Snifter", "Cognac / Snifter / Brandy"),
    ("Tiki", "Tiki"),
    ("Sling", "Sling"),
    ("Pitcher", "Pitcher"),
    ("Goblet", "Goblet"),
    ("Jar", "Jar"),
    ("Copper Mug", "Copper Mug"),
    ("French Press", "French Press"),
    ("Milkshake", "Milkshake"),
    ("Punch Bowl", "Punch Bowl"),
    ("Tea Cup", "Tea Cup"),
]


class CocktailAdminForm(forms.ModelForm):
    # Optional glass type on the Cocktail form (defaults to Highball)
    glass_type = forms.ChoiceField(
        label="Glass type",
        choices=GLASS_TYPE_CHOICES,
        required=False,
        initial="Highball",
    )

    class Meta:
        model = Cocktail
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Pre-populate slug from name (keeps your previous behavior in the UI)
        self.fields["slug"].help_text = "Leave empty to auto-generate from name."

        # If editing, try to preload current glass type from summaries table/view
        if self.instance and self.instance.pk:
            glass = None
            with connection.cursor() as c:
                # Try physical table
                try:
                    c.execute("SELECT glass_type FROM cocktail_summaries WHERE id=%s", [self.instance.pk])
                    row = c.fetchone()
                    if row:
                        glass = row[0]
                except Exception:
                    pass
                # Fallback to view
                if glass is None:
                    try:
                        c.execute("SELECT glass_type FROM cocktail_summary_v WHERE id=%s", [self.instance.pk])
                        row = c.fetchone()
                        if row:
                            glass = row[0]
                    except Exception:
                        pass

            if glass:
                self.fields["glass_type"].initial = glass


@admin.register(Cocktail)
class CocktailAdmin(admin.ModelAdmin):
    form = CocktailAdminForm
    inlines = [CocktailIngredientInline]

    list_display = ("name", "status", "price_display", "abv_display", "image_thumb")
    list_filter = ("status",)
    search_fields = ("name", "slug")
    # keep the convenient auto-fill for slug in the add/change form
    prepopulated_fields = {"slug": ("name",)}

    fieldsets = (
        ("Basics", {"fields": ("name", "slug", "story_long")}),
        ("Media", {"fields": ("image_url", "image_preview", "video_url")}),
        ("Status & system", {"fields": ("status", "price_auto_display", "created_at", "updated_at", "glass_type")}),
    )
    readonly_fields = ("image_preview", "price_auto_display", "created_at", "updated_at")

    # ---------------- helpers ----------------

    def _fetch_summary(self, obj):
        """Return (price_suggested, abv_percent) or (None, None)."""
        price = abv = None
        with connection.cursor() as c:
            # Preferred: view
            try:
                c.execute(
                    "SELECT price_suggested, abv_percent FROM cocktail_summary_v WHERE id=%s",
                    [obj.pk],
                )
                row = c.fetchone()
                if row:
                    price, abv = row
            except Exception:
                pass

            # Fallback: physical table (if present)
            if price is None and abv is None:
                try:
                    c.execute(
                        "SELECT price_suggested, abv_percent FROM cocktail_summaries WHERE id=%s",
                        [obj.pk],
                    )
                    row = c.fetchone()
                    if row:
                        price, abv = row
                except Exception:
                    pass
        return price, abv

    @staticmethod
    def _fmt2(x):
        return f"{Decimal(x):.2f}"

    def image_preview(self, obj):
        url = (obj.image_url or "").strip()
        if not url:
            url = "https://res.cloudinary.com/dau9qbp3l/image/upload/v1755145790/no-photo-master.png"
        return mark_safe(f'<img src="{url}" style="height:90px;border-radius:8px;" />')
    image_preview.short_description = "Preview"

    def image_thumb(self, obj):
        url = (obj.image_url or "").strip()
        if not url:
            url = "https://res.cloudinary.com/dau9qbp3l/image/upload/v1755145790/no-photo-master.png"
        return mark_safe(f'<img src="{url}" style="height:22px;border-radius:4px;" />')
    image_thumb.short_description = "Image"

    def price_auto_display(self, obj):
        price, _abv = self._fetch_summary(obj)
        return self._fmt2(price) if price is not None else "—"
    price_auto_display.short_description = "Price (auto)"

    def price_display(self, obj):
        price, _abv = self._fetch_summary(obj)
        return self._fmt2(price) if price is not None else "—"
    price_display.short_description = "Price"

    def abv_display(self, obj):
        _price, abv = self._fetch_summary(obj)
        return self._fmt2(abv) if abv is not None else "—"
    abv_display.short_description = "ABV %"

    # Persist selected glass type when possible (no-op if only a view exists)
    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        selected_glass = form.cleaned_data.get("glass_type") or "Highball"
        with connection.cursor() as c:
            try:
                c.execute(
                    """
                    INSERT INTO cocktail_summaries (id, slug, name, glass_type)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE glass_type = VALUES(glass_type)
                    """,
                    [obj.pk, obj.slug, obj.name, selected_glass],
                )
            except Exception:
                try:
                    c.execute(
                        "UPDATE cocktail_summaries SET glass_type=%s WHERE id=%s",
                        [selected_glass, obj.pk],
                    )
                except Exception:
                    # Only a view available ⇒ nothing to write (that’s OK)
                    pass
