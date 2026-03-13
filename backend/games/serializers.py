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
            "small": obj.cover_small.url,
            "medium": obj.cover_medium.url,
            "large": obj.cover_large.url,
        }


 # This provides all details about game, 
class GamesSerializer(serializers.ModelSerializer):
    class Meta:
        model = Games
        fields = ['id', 'name', 'description', 'cover_image', 'tags', 'rating', 'developer', 'publisher', 'price', 'trailer_1']






class GameSerializer(serializers.ModelSerializer):
    class Meta:
        model = Games
        fields = ['id', 'name', 'cover_image'] # Adjust fields based on your model
