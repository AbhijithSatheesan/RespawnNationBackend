from rest_framework import serializers
from django.db.models import Sum
from .models import (
    Tournament, FootballStanding, FootballMatch, 
    Participant, BattleRoyaleMatch, BattleRoyaleResult
)

# ==========================================
# 1. TOURNAMENT LIST SERIALIZER (For Dashboard)
# ==========================================
class TournamentSerializer(serializers.ModelSerializer):
    game_name = serializers.CharField(source='game.name', read_only=True)
    winner_name = serializers.CharField(source='winner.user.username', read_only=True, default="TBD")
    current_participants = serializers.IntegerField(source='participants.count', read_only=True)
    is_registered = serializers.SerializerMethodField()

    type_name = serializers.CharField(source='tournament_type.name', read_only=True)
    
    
    # FIX: Change this to a SerializerMethodField
    current_prize_pool = serializers.SerializerMethodField()
    
    # The 3 Image Layers
    custom_banner = serializers.SerializerMethodField()
    promo_background = serializers.SerializerMethodField()
    format_overlay = serializers.SerializerMethodField()
    
    class Meta:
        model = Tournament
        fields = [
            'id', 'title', 'status', 'max_players', 'registration_deadline', 
            'game_name', 'winner_name', 'current_participants','is_registered',
            'custom_banner', 'promo_background','type_name',  'format_overlay', 'entry_fee', 'current_prize_pool'
        ]

    # FIX: Manually grab the property and force it into a JSON-safe float
    def get_current_prize_pool(self, obj):
        return float(obj.current_prize_pool)

    # Checks if the user already registered to the tournament
    def get_is_registered(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return Participant.objects.filter(tournament=obj, user=request.user).exists()
        return False
    
    # Helper function to safely build image URLs
    def get_absolute_image_url(self, photo):
        if not photo: return None
        request = self.context.get('request')
        if request: return request.build_absolute_uri(photo.url)
        return photo.url

    def get_custom_banner(self, obj):
        return self.get_absolute_image_url(obj.custom_banner)

    def get_promo_background(self, obj):
        if obj.game and obj.game.promo_background:
            return self.get_absolute_image_url(obj.game.promo_background)
        # Safely handling ImageKit fields if they exist
        elif obj.game and hasattr(obj.game, 'cover_image') and obj.game.cover_image:
            return self.get_absolute_image_url(obj.game.cover_image)
        return None

    def get_format_overlay(self, obj):
        if obj.tournament_type and obj.tournament_type.format_overlay:
            return self.get_absolute_image_url(obj.tournament_type.format_overlay)
        return None


# ==========================================
# 2. FOOTBALL SERIALIZERS
# ==========================================
class FootballStandingSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='participant.user.username', read_only=True)
    
    class Meta:
        model = FootballStanding
        fields = ['id', 'username', 'group_name', 'matches_played', 'points', 'goals_scored', 'goals_conceded']


class FootballMatchSerializer(serializers.ModelSerializer):
    player_1_name = serializers.CharField(source='player_1.user.username', read_only=True, default="TBD")
    player_2_name = serializers.CharField(source='player_2.user.username', read_only=True, default="TBD")
    winner_name = serializers.CharField(source='winner.user.username', read_only=True, default="Draw / Pending")
    
    class Meta:
        model = FootballMatch
        fields = ['id', 'stage', 'round_name', 'player_1_name', 'player_2_name', 'p1_score', 'p2_score', 'winner_name', 'is_completed']


# ==========================================
# 3. BATTLE ROYALE SERIALIZERS
# ==========================================
class BattleRoyaleMatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = BattleRoyaleMatch
        fields = ['id', 'match_number', 'is_completed']




# <<<<<------------------ TOURNAMENT DETAIL SERIALIZER -------------------------->>>>>



class TournamentDetailSerializer(serializers.ModelSerializer):
    game_name = serializers.CharField(source='game.name', read_only=True)
    engine_code = serializers.CharField(source='tournament_type.engine_code', read_only=True, default="unknown")
    winner_name = serializers.CharField(source='winner.user.username', read_only=True, default=None)
    type_name = serializers.CharField(source='tournament_type.name', read_only=True)
    type_description = serializers.CharField(source='tournament_type.description', read_only=True)
    
    # Custom fields that require methods to calculate/fetch data
    custom_banner = serializers.SerializerMethodField()
    is_registered = serializers.SerializerMethodField()
    current_participants = serializers.SerializerMethodField() # FIX: Added method field
    
    # Format-specific fields
    standings = serializers.SerializerMethodField()
    matches = serializers.SerializerMethodField()
    br_lobbies = serializers.SerializerMethodField()
    br_leaderboard = serializers.SerializerMethodField()

    class Meta:
        model = Tournament
        fields = [
            'id', 'title', 'status', 'max_players', 'current_participants', 
            'entry_fee', 'current_prize_pool', 'registration_deadline',
            'game_name', 'engine_code', 'type_description', 'type_name', 
            'custom_banner', 'winner_name', 'is_registered',
            'standings', 'matches', 'br_lobbies', 'br_leaderboard'
        ]

    def get_custom_banner(self, obj):
        if not obj.custom_banner: return None
        request = self.context.get('request')
        if request: return request.build_absolute_uri(obj.custom_banner.url)
        return obj.custom_banner.url

    # --- Participant & Registration Data ---
    def get_current_participants(self, obj):
        # NOTE: If your Tournament model uses a different related name than 'participants', 
        # (for example, 'registrations'), change this to obj.registrations.count()
        return obj.participants.count()

    def get_is_registered(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            # Matches the related name used in get_current_participants
            return obj.participants.filter(user=request.user).exists()
        return False

    # --- Football Data Fetchers ---
    def get_standings(self, obj):
        if obj.tournament_type and obj.tournament_type.engine_code == 'world_cup':
            standings = FootballStanding.objects.filter(participant__tournament=obj).order_by('group_name', '-points', '-goals_scored')
            return FootballStandingSerializer(standings, many=True).data
        return []

    def get_matches(self, obj):
        if obj.tournament_type and obj.tournament_type.engine_code == 'world_cup':
            matches = obj.football_matches.all().order_by('stage', 'id')
            return FootballMatchSerializer(matches, many=True).data
        return []

    # --- Battle Royale Data Fetchers ---
    def get_br_lobbies(self, obj):
        if obj.tournament_type and obj.tournament_type.engine_code == 'battle_royale':
            lobbies = obj.br_matches.all().order_by('match_number')
            return BattleRoyaleMatchSerializer(lobbies, many=True).data
        return []

    def get_br_leaderboard(self, obj):
        if obj.tournament_type and obj.tournament_type.engine_code == 'battle_royale':
            # Group by participant, sum their kills and points, order by highest points
            results = BattleRoyaleResult.objects.filter(match__tournament=obj)\
                .values('participant__user__username')\
                .annotate(
                    total_kills=Sum('kills'), 
                    total_pts=Sum('total_points')
                ).order_by('-total_pts', '-total_kills')
            
            # Format cleanly for React
            leaderboard = [
                {
                    'username': res['participant__user__username'],
                    'total_kills': res['total_kills'] or 0,
                    'total_points': res['total_pts'] or 0
                } for res in results
            ]
            return leaderboard
        return []