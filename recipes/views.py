from django.shortcuts import render

def index(request):
    return render(request, 'recipes/index.html', {
        'recipes': [
            {'title': 'Spaghetti Carbonara', 'desc': '15 min • Comfort'},
            {'title': 'Chocolate Chip Cookies', 'desc': 'Easy • Crowd favorite'},
        ]
    })