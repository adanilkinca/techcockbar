# cocktails/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.apps import apps

from .models import Cocktail, Ingredient, CocktailIngredient
from .forms import CocktailIngredientInlineForm, CocktailAdminForm


# ---------- helpers ----------

def _has_field(model, name: str) -> bool:
    return any(getattr(f, "concrete", False) and f.name == name for f in model._meta.get_fields())

def _concrete_field_names(model, include_rel=True):
    names = []
    for f in model._meta.get_fields():
        if not getattr(f, "concrete", False):
            continue
        if not include_rel and (getattr(f, "many_to_many", False) or getattr(f, "one_to_many", False)):
            continue
        names.append(f.name)
    return names

def _get_model(name: str):
    try:
        return apps.get_model("cocktails", name)
    except LookupError:
        return None

def _cloudinary_square(url: str, size: int = 400) -> str:
    """
    Insert a Cloudinary transform to deliver a square image without re-uploading.
    Example:
      .../upload/v123/foo.jpg -> .../upload/c_fill,ar_1:1,g_auto,q_auto,f_auto,w_400/v123/foo.jpg
    """
    if not url or "/upload/" not in url:
        return url or ""
    return url.replace(
        "/upload/",
        f"/upload/c_fill,ar_1:1,g_auto,q_auto,f_auto,w_{size}/",
        1,
    )


# ---------- inlines ----------

class CocktailIngredientInline(admin.TabularInline):
    model = CocktailIngredient
    form = CocktailIngredientInlineForm
    extra = 0

    def get_fields(self, request, obj=None):
        wanted = ["seq", "ingredient", "amount_input", "unit_input", "amount_oz", "prep_note", "is_optional"]
        return [f for f in wanted if _has_field(self.model, f)]

    def get_readonly_fields(self, request, obj=None):
        ro = []
        if _has_field(self.model, "amount_oz"):
            ro.append("amount_oz")
        return ro

    def get_ordering(self, request):
        return ("seq",) if _has_field(self.model, "seq") else None


# ---------- main cocktail admin ----------

@admin.register(Cocktail)
class CocktailAdmin(admin.ModelAdmin):
    form = CocktailAdminForm
    inlines = [CocktailIngredientInline]
    readonly_fields = ("image_preview",)

    def get_list_display(self, request):
        candidates = ["id", "name", "status", "cocktail_abv", "cocktail_price", "created_at", "updated_at"]
        cols = [c for c in candidates if _has_field(Cocktail, c)]
        # small square thumbnail column
        if "name" in cols:
            cols.insert(1, "thumb")
        else:
            cols.append("thumb")
        return tuple(cols)

    def thumb(self, obj):
        url = getattr(obj, "image_url", None) or getattr(obj, "photo_url", None)
        if not url:
            return "—"
        sq = _cloudinary_square(url, size=120)
        return format_html(
            '<img src="{}" style="height:28px;width:28px;object-fit:cover;border-radius:4px;" />', sq
        )
    thumb.short_description = " "

    def get_prepopulated_fields(self, request, obj=None):
        if _has_field(Cocktail, "slug") and _has_field(Cocktail, "name"):
            return {"slug": ("name",)}
        return {}

    def image_preview(self, obj):
        url = getattr(obj, "image_url", None) or getattr(obj, "photo_url", None)
        if url:
            sq = _cloudinary_square(url, size=400)
            return format_html('<img src="{}" style="max-width:240px;height:auto;border-radius:8px;" />', sq)
        return "—"
    image_preview.short_description = "Preview"


# ---------- Ingredient admin ----------

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    search_fields = ("name",)
    list_display = tuple([c for c in ("id", "name", "abv") if _has_field(Ingredient, c)])


# ---------- Read-only view models (if present) ----------

def _register_readonly(model):
    class ReadOnlyAdmin(admin.ModelAdmin):
        list_per_page = 50

        def get_list_display(self, request):
            return [f for f in _concrete_field_names(model, include_rel=False)]

        def get_readonly_fields(self, request, obj=None):
            return _concrete_field_names(model)

        def has_add_permission(self, request): return False
        def has_change_permission(self, request, obj=None): return False
        def has_delete_permission(self, request, obj=None): return False

        def get_ordering(self, request):
            return ("pk",)

        search_fields = ("cocktail__name", "cocktail__id", "cocktail__slug")

    try:
        admin.site.register(model, ReadOnlyAdmin)
    except admin.sites.AlreadyRegistered:
        pass


CocktailSummary   = _get_model("CocktailSummary")
CocktailPrice     = _get_model("CocktailPrice")
CocktailAllergens = _get_model("CocktailAllergens")

for m in (CocktailSummary, CocktailPrice, CocktailAllergens):
    if m is not None:
        _register_readonly(m)


# ---------- PricingSettings (editable knobs like labor cost) ----------

PricingSettings = _get_model("PricingSettings")
if PricingSettings is not None:
    class PricingSettingsAdmin(admin.ModelAdmin):
        def get_list_display(self, request):
            return tuple(_concrete_field_names(PricingSettings, include_rel=False))
        def get_readonly_fields(self, request, obj=None):
            return ()
        list_per_page = 20

    try:
        admin.site.register(PricingSettings, PricingSettingsAdmin)
    except admin.sites.AlreadyRegistered:
        pass
