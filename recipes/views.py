from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.shortcuts import render, redirect
from django.http import JsonResponse
from .models import Recipe, MealPlan
from .ingredient_parser import normalize_ingredient, aggregate_ingredients, format_quantity
import re
from datetime import datetime, timedelta

class RecipeListView(ListView):
    model = Recipe
    template_name = 'recipes/index.html'
    context_object_name = 'recipes'
    paginate_by = 12

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        meal_plans = MealPlan.objects.all().select_related('recipe').order_by('day')
        days_dict = {}
        for day, day_name in MealPlan.DAYS_OF_WEEK:
            days_dict[day] = {'name': day_name, 'recipes': []}
        
        for mp in meal_plans:
            days_dict[mp.day]['recipes'].append({
                'id': mp.id,
                'recipe': mp.recipe,
            })
        
        ctx['meal_plan_days'] = [days_dict[day[0]] for day in MealPlan.DAYS_OF_WEEK]
        return ctx

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


def get_meal_plan(request):
    """Return meal plan as JSON for AJAX requests."""
    meal_plans = MealPlan.objects.all().select_related('recipe').order_by('day')
    days = {day[0]: {'day_name': day[1], 'recipes': []} for day in MealPlan.DAYS_OF_WEEK}
    
    for mp in meal_plans:
        days[mp.day]['recipes'].append({
            'id': mp.id,
            'recipe_id': mp.recipe.id,
            'recipe_title': mp.recipe.title,
        })
    
    return JsonResponse(list(days.values()), safe=False)


def add_to_meal_plan(request, recipe_id):
    """Add a recipe to the meal plan for a specific day."""
    if request.method == 'POST':
        day = request.POST.get('day')
        if day:
            recipe = Recipe.objects.get(pk=recipe_id)
            MealPlan.objects.create(recipe=recipe, day=day)
            return redirect('recipes:list')
    
    recipe = Recipe.objects.get(pk=recipe_id)
    return render(request, 'recipes/add_to_meal_plan.html', {
        'recipe': recipe,
        'days': MealPlan.DAYS_OF_WEEK,
    })


def remove_from_meal_plan(request, meal_plan_id):
    """Remove a recipe from the meal plan."""
    meal_plan = MealPlan.objects.get(pk=meal_plan_id)
    meal_plan.delete()
    return redirect('recipes:list')


def clear_meal_plan(request):
    """Clear all recipes from the meal plan."""
    if request.method == 'POST':
        MealPlan.objects.all().delete()
        return redirect('recipes:list')
    return render(request, 'recipes/confirm_clear_meal_plan.html')


def create_meal_plan_bulk(request):
    """Create meal plan entries from selected recipes with auto-assigned days starting from a start date."""
    if request.method == 'POST':
        # Support explicit assignments: multiple values like 'assignments' = 'recipeid|YYYY-MM-DD'
        assignments = request.POST.getlist('assignments')
        if assignments:
            days_of_week = [day[0] for day in MealPlan.DAYS_OF_WEEK]
            for a in assignments:
                try:
                    recipe_id, date_str = a.split('|', 1)
                    recipe = Recipe.objects.get(pk=int(recipe_id))
                    current_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                    day_name = days_of_week[current_date.weekday()]
                    MealPlan.objects.create(recipe=recipe, day=day_name)
                except Exception:
                    # skip invalid entries
                    continue
            return redirect('recipes:list')

        # Backwards compatible: simple start_date + recipe_ids
        recipe_ids = request.POST.getlist('recipe_ids')
        start_date_str = request.POST.get('start_date')
        
        if recipe_ids and start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            except ValueError:
                start_date = None
            
            if start_date:
                recipes = Recipe.objects.filter(pk__in=recipe_ids)
                
                # Map date to day of week
                days_of_week = [day[0] for day in MealPlan.DAYS_OF_WEEK]
                
                for idx, recipe in enumerate(recipes):
                    current_date = start_date + timedelta(days=idx)
                    day_name = days_of_week[current_date.weekday()]  # 0=Monday, 6=Sunday
                    MealPlan.objects.create(recipe=recipe, day=day_name)
                
                return redirect('recipes:list')
    
    # GET request: show form with selected recipes
    recipe_ids = request.GET.getlist('recipe_ids')
    recipes = Recipe.objects.filter(pk__in=recipe_ids)
    
    return render(request, 'recipes/meal_plan_select_date.html', {
        'selected_recipes': recipes,
        'recipe_ids': recipe_ids,
    })

