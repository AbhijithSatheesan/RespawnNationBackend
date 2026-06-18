from django.shortcuts import render
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny
from django.shortcuts import get_object_or_404
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from django.db.models import Q
import random

from .models import Games, GameCategory
from .serializers import GamesSerializer,GameCardSerializer, GameSerializer



# Create your views here.


@api_view(['GET'])
@authentication_classes([]) 
@permission_classes([AllowAny])
def browse_games(request):

    # 1. Limit to 8 games per row (Perfect for horizontal scrolling)
    trending_category = get_object_or_404(GameCategory, name="Trending")
    trending_games = trending_category.games.all()[:20]

    top_rated_category = get_object_or_404(GameCategory, name='Top Rated')
    top_rated_games = top_rated_category.games.all()[:20]

    # 2. Limit to only 4 main categories to prevent endless scrolling
    main_categories = GameCategory.objects.filter(main_category=True)[:5]
    category_games = {}

    for category in main_categories:
        # 3. Limit to 8 games per category
        games_in_category = category.games.all()[:8]
        # Only add the category if it actually has games in it!
        if games_in_category.exists():
            category_games[category.name] = GameCardSerializer(games_in_category, many=True).data

    data = {
        "Trending_games": GameCardSerializer(trending_games, many=True).data if trending_games else None,
        "Top_rated_games": GameCardSerializer(top_rated_games, many=True).data if top_rated_games else None,
        "Main_category": category_games,
    }

    return Response(data)





@api_view(['GET'])
def search_games(request):
    query = request.GET.get('q', '').strip()
    
    if len(query) > 0:
        games = Games.objects.filter(name__icontains=query)[:5]
        
        # ADDED: context={'request': request} 
        # This allows the serializer to build full local URLs if needed
        serializer = GameCardSerializer(games, many=True, context={'request': request})
        
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    return Response([], status=status.HTTP_200_OK)






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




class GameSearchView(generics.ListAPIView):
    permission_classes = [permissions.AllowAny] # Anyone can search games
    serializer_class = GameSerializer

    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        if query:
            # Search by name (case insensitive)
            return Games.objects.filter(name__icontains=query)[:10] # Limit to 10 results
        return Games.objects.none()
    



# GamePage
@api_view(['GET'])
@authentication_classes([])
@permission_classes([AllowAny])
def game_detail(request, pk):
    game = get_object_or_404(Games, pk= pk)
    serializer = GamesSerializer(game)
    return Response(serializer.data)



@api_view(['GET'])
def get_games_by_category(request, category_name):
    try:
        # Use name__iexact for case-insensitive matching just to be safe
        category = GameCategory.objects.get(name__iexact=category_name)
        games = Games.objects.filter(categories=category)
        
        serializer = GameCardSerializer(games, many=True)
        
        return Response({
            "category_name": category.name,
            "games": serializer.data
        }, status=status.HTTP_200_OK)
        
    except GameCategory.DoesNotExist:
        return Response({"error": "Category not found"}, status=status.HTTP_404_NOT_FOUND)