from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import render
from .models import Recipe
from .ingredient_parser import normalize_ingredient, aggregate_ingredients, format_quantity
import re

class RecipeListView(ListView):
    model = Recipe
    template_name = 'recipes/index.html'
    context_object_name = 'recipes'
    paginate_by = 12

class RecipeDetailView(DetailView):
    model = Recipe
    template_name = 'recipes/detail.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        obj = self.get_object()

        # Ingredients: split comma-separated list into items
        ingredients_raw = obj.ingredients or ''
        ingredients_list = [i.strip() for i in ingredients_raw.split(',') if i.strip()]

        # Steps: split on blank lines (double newlines) or single newlines as fallback
        steps_raw = obj.steps or ''
        # First try splitting on blank lines
        steps_list = [s.strip() for s in re.split(r'\r?\n\r?\n', steps_raw) if s.strip()]
        if not steps_list:
            steps_list = [s.strip() for s in steps_raw.splitlines() if s.strip()]

        # Detect whether the user already numbered the steps (e.g., "1. Step")
        steps_numbered = False
        if steps_list:
            steps_numbered = bool(re.match(r"^\s*\d+[\.|\)]\s+", steps_list[0]))

        # Tags
        tags_raw = getattr(obj, 'tags', '') or ''
        tags_list = [t.strip() for t in tags_raw.split(',') if t.strip()]

        ctx.update({
            'ingredients_list': ingredients_list,
            'steps_list': steps_list,
            'tags_list': tags_list,
            'steps_numbered': steps_numbered,
        })
        return ctx

class RecipeCreateView(CreateView):
    model = Recipe
    fields = ['title','author','description','prep_time_minutes','cook_time_minutes','ingredients','steps','tags']
    template_name = 'recipes/form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from .ingredient_parser import UNIT_MAP
        ctx['unit_options'] = sorted(set(UNIT_MAP.values()))
        ctx['ingredients_raw'] = ''
        return ctx

class RecipeUpdateView(UpdateView):
    model = Recipe
    fields = ['title','author','description','prep_time_minutes','cook_time_minutes','ingredients','steps','tags']
    template_name = 'recipes/form.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        from .ingredient_parser import UNIT_MAP
        ctx['unit_options'] = sorted(set(UNIT_MAP.values()))
        ctx['ingredients_raw'] = self.get_object().ingredients or ''
        return ctx

class RecipeDeleteView(DeleteView):
    model = Recipe
    template_name = 'recipes/confirm_delete.html'
    success_url = reverse_lazy('recipes:list')


def shopping_list(request):
    """Create a shopping list from selected recipes.

    Parses ingredients from the new 4-field format (qty, unit, name, optional desc)
    and aggregates by ingredient name with quantity consolidation.
    """
    if request.method == 'POST':
        ids = request.POST.getlist('selected')
    else:
        ids = request.GET.getlist('selected')

    recipes = Recipe.objects.filter(pk__in=ids)

    # Parse and aggregate ingredients
    ingredients_dict = {}  # ingredient_name -> (quantity, unit)
    recipe_sources = {}    # ingredient_name -> list of recipe titles
    
    for r in recipes:
        # Split by comma for comma-separated ingredients (format: "qty unit name (optional)")
        for ingredient_item in (r.ingredients or '').split(','):
            ingredient_item = ingredient_item.strip()
            if not ingredient_item:
                continue
            
            # Parse: "1 cup yellow onion (diced)" or "2 tbsp flour" or "salt"
            # Pattern: optional_qty optional_unit required_name (optional_desc)
            match = re.match(r'^([0-9.]+)?\s*([a-z]+)?\s*(.+?)(?:\s*\(([^)]+)\))?\s*$', ingredient_item, re.IGNORECASE)
            
            if match:
                qty_str = match.group(1) or ''
                unit = match.group(2) or ''
                ing_name = match.group(3).strip() if match.group(3) else ''
                
                # Convert qty_str to float
                try:
                    qty = float(qty_str) if qty_str else None
                except ValueError:
                    qty = None
                
                if ing_name:
                    # Track which recipes this ingredient came from
                    if ing_name not in recipe_sources:
                        recipe_sources[ing_name] = []
                    if r.title not in recipe_sources[ing_name]:
                        recipe_sources[ing_name].append(r.title)
                    
                    # Store for aggregation
                    if ing_name not in ingredients_dict:
                        ingredients_dict[ing_name] = (qty, unit)
                    else:
                        # Aggregate: add quantities if units match
                        existing_qty, existing_unit = ingredients_dict[ing_name]
                        
                        if unit == existing_unit or (not unit and not existing_unit):
                            new_qty = (existing_qty or 0) + (qty or 0) if qty else existing_qty
                            ingredients_dict[ing_name] = (new_qty if new_qty else None, unit or existing_unit)
                        else:
                            # Different units: keep the first one and accumulate qty if both have values
                            if existing_qty and qty:
                                new_qty = existing_qty + qty
                                ingredients_dict[ing_name] = (new_qty, existing_unit)

    # Prepare items for template
    items = []
    for ing_name in sorted(ingredients_dict.keys(), key=str.lower):
        qty, unit = ingredients_dict[ing_name]
        qty_display = format_quantity(qty, unit)
        recipe_count = len(recipe_sources.get(ing_name, []))
        items.append({
            'name': ing_name,
            'quantity': qty_display,
            'count': recipe_count,
            'recipes': recipe_sources.get(ing_name, []),
        })

    return render(request, 'recipes/shopping_list.html', {
        'items': items,
        'recipes': recipes,
    })
