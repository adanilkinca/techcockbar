from django import forms
from django.forms.models import BaseInlineFormSet

class CocktailIngredientInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()
        rows = []
        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            cd = form.cleaned_data
            if cd and not cd.get("DELETE", False):
                rows.append(cd)

        if not rows:
            raise forms.ValidationError("Add at least one ingredient line.")

        # If publishing, require at least one non-ice liquid with a positive amount
        status = getattr(self.instance, "status", "draft")
        if status == "published":
            has_non_ice_liquid = any(
                (cd.get("amount_input") or 0) > 0 and
                getattr(cd.get("ingredient"), "type", None) != "ice"
                for cd in rows
            )
            if not has_non_ice_liquid:
                raise forms.ValidationError(
                    "Published cocktails must include at least one non‑ice liquid amount."
                )
