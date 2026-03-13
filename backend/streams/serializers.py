from rest_framework import serializers
from .models import Stream, Games


# The serializer which shows to viewrs
class StreamPublicSerializer(serializers.ModelSerializer):
    hls_url = serializers.ReadOnlyField()


    class Meta:
        model = Stream
        fields = [
            'id',
            'title',
            'description',
            'is_live',
            'playback_id',
            'hls_url',
        ]



# The serializer for owner to see which contains importand infos
class StreamOwnerSerializer(serializers.ModelSerializer):
    ingest_url = serializers.SerializerMethodField()

    class Meta:
        model = Stream
        fields = [
            'id',
            'title',
            'description',
            'is_live',
            'stream_key',
            'playback_id',
            'ingest_url',
        ]

    # This function passes cloudflare global ingest endpoint
    def get_ingest_url(self, obj):
        return "rtmps://live.cloudflare.com/live"
    





class StreamUpdateSerializer(serializers.ModelSerializer):
    game_id = serializers.IntegerField(write_only=True, required=False, allow_null=True)

    class Meta:
        model = Stream
        fields = ['title', 'description', 'is_live', 'game_id','playback_id']

    def update(self, instance, validated_data):
        # Handle Game relationship manually if passed as ID
        game_id = validated_data.pop('game_id', None)
        if game_id:
            try:
                instance.game = Games.objects.get(id=game_id)
            except Games.DoesNotExist:
                pass # Or raise validation error
        
        return super().update(instance, validated_data)