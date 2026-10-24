from django import forms

from .models import Project


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["naam", "opdrachtgever", "status"]

    def clean_naam(self):
        naam = self.cleaned_data["naam"].strip()
        if len(naam) < 5:
            raise forms.ValidationError("De projectnaam moet minstens 5 tekens hebben.")
        return naam
