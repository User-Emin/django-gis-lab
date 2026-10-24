from django.db.models import Count
from django.shortcuts import render

from .models import Project, Tekening


def home(request):
    return render(
        request,
        "kaart/home.html",
        {
            "aantal_projecten": Project.objects.count(),
            "aantal_tekeningen": Tekening.objects.count(),
        },
    )


def tekeningen_langzaam(request):
    """N+1: één query voor de tekeningen, daarna één extra query per tekening voor t.project."""
    tekeningen = Tekening.objects.all()
    return render(
        request,
        "kaart/tekening_tabel.html",
        {"titel": "Tekeningen (N+1)", "tekeningen": tekeningen},
    )


def tekeningen_snel(request):
    """select_related: één JOIN-query, het project zit al in het resultaat."""
    tekeningen = Tekening.objects.select_related("project")
    return render(
        request,
        "kaart/tekening_tabel.html",
        {"titel": "Tekeningen (select_related)", "tekeningen": tekeningen},
    )


def projecten_overzicht(request):
    """Les 06, Zelf: tekeningen per project tellen met één query (annotate), niet per project."""
    projecten = Project.objects.annotate(aantal=Count("tekeningen"))
    return render(request, "kaart/project_overzicht.html", {"projecten": projecten})
