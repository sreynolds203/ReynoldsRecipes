from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import render
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


def shopping_list(request):
    """Create a shopping list from selected recipes.

    Collects the `selected` recipe ids from POST (or GET), splits each recipe's
    `ingredients` field by line, normalizes entries, and aggregates identical
    ingredient lines with a simple count.
    """
    if request.method == 'POST':
        ids = request.POST.getlist('selected')
    else:
        ids = request.GET.getlist('selected')

    recipes = Recipe.objects.filter(pk__in=ids)

    ingredients = {}
    for r in recipes:
        for line in (r.ingredients or '').splitlines():
            ing = line.strip()
            if not ing:
                continue
            ingredients[ing] = ingredients.get(ing, 0) + 1

    # Prepare items as a sorted list of (ingredient, count)
    items = sorted(ingredients.items(), key=lambda x: x[0].lower())

    return render(request, 'recipes/shopping_list.html', {
        'items': items,
        'recipes': recipes,
    })
