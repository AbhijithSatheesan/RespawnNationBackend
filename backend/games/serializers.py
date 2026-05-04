from rest_framework import serializers
from .models import Games



# This serializer will only give data just enough for game cards
class GameCardSerializer(serializers.ModelSerializer):
    cover = serializers.SerializerMethodField()

    class Meta:
        model = Games
        fields = ['id', 'name', 'rating', 'cover']

    def get_cover(self, obj):
        if not obj.cover_image:
            return None

        return {
            "medium": obj.cover_image.url,
            "small": obj.cover_image.url, 
            "large": obj.cover_image.url,
        }


class GamesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Games
        fields = [
            'id', 'name', 'description', 'release_year', 'cover_image', 
            'promo_background', 'tags', 'rating', 'developer', 'publisher', 
            'price', 'trailer_1', 'trailer_2', 
            'action', 'graphics', 'story', 'gameplay'
        ]



class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Games
        fields = ['id', 'name', 'cover_image'] # Adjust fields based on your model
