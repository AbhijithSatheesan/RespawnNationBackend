from django.urls import path
from .views import *

urlpatterns = [
    path('browse_games/', browse_games, name= 'browse_games'),
    path('trending_game/', trending_game, name= 'trending_game'),
    path('search/', GameSearchView.as_view(), name='search-games'),
    path('game/<int:pk>/', game_detail, name= 'game_details'),
    path('category/<str:category_name>/', get_games_by_category, name='category-games'),
   
]