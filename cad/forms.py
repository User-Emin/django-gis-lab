from pathlib import Path

from django import forms
from django.conf import settings

from .models import Tekening


class UploadForm(forms.ModelForm):
    """Upload van een DXF. Naam en BAG-pand-id zijn optioneel."""

    class Meta:
        model = Tekening
        fields = ["bestand", "naam", "bag_pand_id"]
        labels = {"bestand": "DXF-bestand", "naam": "Naam", "bag_pand_id": "BAG-pand-id"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["naam"].required = False
        self.fields["bag_pand_id"].required = False
        self.fields["bestand"].widget.attrs["accept"] = ".dxf"

    def clean_bestand(self):
        f = self.cleaned_data["bestand"]
        if Path(f.name).suffix.lower() != ".dxf":
            raise forms.ValidationError("Alleen .dxf-bestanden zijn toegestaan.")
        maximaal = settings.CAD_MAX_UPLOAD_BYTES
        if f.size > maximaal:
            raise forms.ValidationError(
                f"Het bestand is {f.size / 1e6:.1f} MB; het maximum is {maximaal / 1e6:.0f} MB."
            )
        return f

    def clean_bag_pand_id(self):
        waarde = self.cleaned_data["bag_pand_id"].strip()
        if waarde and not (waarde.isdigit() and len(waarde) == 16):
            raise forms.ValidationError("Een BAG-pand-id bestaat uit 16 cijfers.")
        return waarde
