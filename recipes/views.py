from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from .models import Recipe

class RecipeListView(ListView):
    model = Recipe
    template_name = 'recipes/index.html'
    context_object_name = 'recipes'
    paginate_by = 12

class RecipeDetailView(DetailView):
    model = Recipe
    template_name = 'recipes/detail.html'

class RecipeCreateView(CreateView):
    model = Recipe
    fields = ['title','description','prep_time_minutes','ingredients','steps']
    template_name = 'recipes/form.html'

class RecipeUpdateView(UpdateView):
    model = Recipe
    fields = ['title','description','prep_time_minutes','ingredients','steps']
    template_name = 'recipes/form.html'

class RecipeDeleteView(DeleteView):
    model = Recipe
    template_name = 'recipes/confirm_delete.html'
    success_url = reverse_lazy('recipes:list')
