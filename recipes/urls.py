from django.urls import path
from . import views

app_name = 'recipes'

urlpatterns = [
    path('', views.RecipeListView.as_view(), name='list'),
    path('new/', views.RecipeCreateView.as_view(), name='create'),
    path('<int:pk>/', views.RecipeDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.RecipeUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.RecipeDeleteView.as_view(), name='delete'),
    path('shopping-list/', views.shopping_list, name='shopping_list'),
    path('meal-plan/api/', views.get_meal_plan, name='meal_plan_api'),
    path('meal-plan/create-bulk/', views.create_meal_plan_bulk, name='create_meal_plan_bulk'),
    path('<int:recipe_id>/add-to-meal-plan/', views.add_to_meal_plan, name='add_to_meal_plan'),
    path('meal-plan/<int:meal_plan_id>/remove/', views.remove_from_meal_plan, name='remove_from_meal_plan'),
    path('meal-plan/clear/', views.clear_meal_plan, name='clear_meal_plan'),
]
