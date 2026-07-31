from rest_framework import serializers
from .models import Stream
from games.models import Games
from tournaments.models import Tournament 

# 1. What the public sees (Watch Page / Feed)
class StreamPublicSerializer(serializers.ModelSerializer):
    hls_url = serializers.ReadOnlyField()
    streamer_name = serializers.CharField(source='user.username', read_only=True)
    game_name = serializers.CharField(source='game.name', read_only=True)
    
    # NEW: Resolve the thumbnail dynamically
    display_thumbnail = serializers.SerializerMethodField()

    class Meta:
        model = Stream
        fields = [
            'id', 'title', 'description', 'is_live', 
            'playback_id', 'hls_url', 'streamer_name', 'game_name',
            'stream_type', 'external_url', 
            'display_thumbnail' # <-- Add it to fields
        ]

    def get_display_thumbnail(self, obj):
        request = self.context.get('request')
        url = None

        # 1. Check if the stream has a custom thumbnail
        if obj.thumbnail:
            url = obj.thumbnail.url
        # 2. Fallback: check if a game exists AND has a promo background
        elif obj.game and obj.game.promo_background:
            url = obj.game.promo_background.url
            
        # 3. If a valid URL is found, return the absolute URI for React
        if url and request:
            return request.build_absolute_uri(url)
            
        # 4. If neither exists, return None (React will use streamcover.png)
        return None

# 2. What the creator sees (Dashboard)
class StreamOwnerSerializer(serializers.ModelSerializer):
    ingest_url = serializers.SerializerMethodField()

    class Meta:
        model = Stream
        fields = [
            'id', 'title', 'description', 'is_live', 
            'stream_key', 'playback_id', 'ingest_url',
            'stream_type', 'external_url' 
        ]

    def get_ingest_url(self, obj):
        # Only return RTMP URL if it's Cloudflare
        if obj.stream_type == 'CLOUDFLARE':
            return "rtmps://live.cloudflare.com/live"
        return None

# 3. How the creator updates their stream
class StreamUpdateSerializer(serializers.ModelSerializer):
    game_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)
    active_tournament_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Stream
        fields = [
            'title', 'description', 'is_live', 'game_id', 'playback_id',
            'stream_type', 'external_url', 'active_tournament_id' 
        ]

    def update(self, instance, validated_data):
        game_id = validated_data.pop('game_id', None)
        if game_id:
            try:
                instance.game = Games.objects.get(id=game_id)
            except Games.DoesNotExist:
                pass
        
        # Manually handle Tournament relationship
        tourney_id = validated_data.pop('active_tournament_id', None)
        if tourney_id:
            try:
                instance.active_tournament = Tournament.objects.get(id=tourney_id)
            except Tournament.DoesNotExist:
                pass
        
        return super().update(instance, validated_data)