from django.db.models import Count
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from .forms import ProjectForm
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


class ProjectLijst(ListView):
    """Les 07: klassegebaseerde lijstview. Standaard template: kaart/project_list.html."""

    model = Project
    paginate_by = 10

    def get_queryset(self):
        # annotate (GROUP BY) negeert Meta.ordering: zelf sorteren, anders waarschuwt paginering
        return Project.objects.annotate(aantal=Count("tekeningen")).order_by("naam")


class ProjectDetail(DetailView):
    model = Project

    def get_queryset(self):
        return Project.objects.prefetch_related("tekeningen")


class ProjectNieuw(CreateView):
    model = Project
    form_class = ProjectForm
    success_url = reverse_lazy("kaart:project_lijst")


class ProjectBewerk(UpdateView):
    """Les 07, Zelf: bewerken met hetzelfde formulier (template project_form.html)."""

    model = Project
    form_class = ProjectForm
    success_url = reverse_lazy("kaart:project_lijst")
