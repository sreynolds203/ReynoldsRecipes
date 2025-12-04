from django.urls import path
from . import views

app_name = 'recipes'

urlpatterns = [
    path('', views.RecipeListView.as_view(), name='list'),
    path('new/', views.RecipeCreateView.as_view(), name='create'),
    path('<int:pk>/', views.RecipeDetailView.as_view(), name='detail'),
    path('<int:pk>/edit/', views.RecipeUpdateView.as_view(), name='update'),
    path('<int:pk>/delete/', views.RecipeDeleteView.as_view(), name='delete'),
]
