from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
import random

from .models import Games, GameCategory
from .serializers import GamesSerializer
from .serializers import GameCardSerializer


# Create your views here.


@api_view(['GET'])
@authentication_classes([]) 
@permission_classes([AllowAny])
def browse_games(request):

    # Fetch the tending games from database
    trending_category = get_object_or_404(GameCategory, name= "Trending")
    trending_games = trending_category.games.all()[:10]

    # Fetch the top rated games
    top_rated_category = get_object_or_404(GameCategory, name= 'Top Rated')
    top_rated_games = top_rated_category.games.all()[:15]

    # Fetch main category, the items in main categry will be shown below trending and top rated in browse page react
    main_category = GameCategory.objects.filter(main_category = True).prefetch_related('games')
    # Lets cretate a dictionay so that we can send categroy name as key and games in it as value
    category_games = {}

    # loop over categories and fetch games in it and pass them to dictionary
    for category in main_category:
        games_in_category = category.games.all()[:15]
        category_games[category.name] = GameCardSerializer(games_in_category, many= True).data


    data = {
        "Trending_games" : GameCardSerializer(trending_games, many= True).data if trending_games else None,
        "Top_rated_games" : GameCardSerializer(top_rated_games, many= True).data if top_rated_games else None,
        "Main_category" : category_games,

    }

    return Response(data)










# # 1. OPTIMIZE THE QUERY
# # Tell Django: "Get categories, and while you're at it, grab all their games too."
# main_categories = Category.objects.filter(main_category=True).prefetch_related('games') 

# category_games = {}

# # 2. RUN THE LOOP
# # Now, 'category.games.all()' hits the cache (RAM), NOT the database. It is instant.
# for category in main_categories:
#     category_games[category.name] = GamesSerializer(category.games.all(), many=True).data




@api_view(['GET'])
@authentication_classes([])
def trending_game(request):
    trending_category = get_object_or_404(GameCategory, name= "Trending")    
    trending_games = trending_category.games.all()
    
    # Now select a random game from trending_games
    count = trending_games.count()
    random_trending_game= trending_games[random.randint(0, count- 1)] if count > 0 else None

    data = {
        "trending_game" : GamesSerializer(random_trending_game).data if random_trending_game else None
    }

    return Response(data)


from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.db.models import Q
from .models import Games
from .serializers import  GameSerializer

class GameSearchView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny] # Anyone can search games
    serializer_class = GameSerializer

    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        if query:
            # Search by name (case insensitive)
            return Games.objects.filter(name__icontains=query)[:10] # Limit to 10 results
        return Games.objects.none()