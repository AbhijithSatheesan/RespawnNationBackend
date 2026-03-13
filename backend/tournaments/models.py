from django.db import models
from games.models import Games

# Create your models here.

from django.db import models
from django.conf import settings

# 1. THE TOURNAMENT (The Main Event)
class Tournament(models.Model):
    STATUS_CHOICES = [
        ('REGISTRATION', 'Registration Open'),
        ('GENERATING', 'Generating Brackets'),
        ('LIVE', 'Live'),
        ('COMPLETED', 'Completed'),
    ]
    title = models.CharField(max_length=200)
    game = models.ForeignKey(Games, on_delete= models.SET_NULL, null= True, blank= True, related_name= 'Tournaments')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='REGISTRATION')
    max_players = models.IntegerField(default=32)
    registration_deadline = models.DateTimeField()

    def __str__(self):
        return self.title



class Participant(models.Model):
    """
    Every user who clicks 'Join' gets one of these. 
    It connects them to the Tournament.
    """
    tournament = models.ForeignKey('Tournament', on_delete=models.CASCADE, related_name='participants')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    registered_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        # Prevents a user from joining the same tournament twice
        unique_together = ('user', 'tournament')

    def __str__(self):
        return f"{self.user.username} - {self.tournament.title}"


# ==========================================
# 2. FOOTBALL: GROUP STAGE SCORECARD
# ==========================================
class FootballStanding(models.Model):
    """
    If they are playing FIFA, this acts as their row in the Group Table.
    It links directly to their Participant ticket.
    """
    participant = models.OneToOneField(Participant, on_delete=models.CASCADE, related_name='football_stats')
    group_name = models.CharField(max_length=50) # e.g., 'Group A'
    
    matches_played = models.IntegerField(default=0)
    points = models.IntegerField(default=0)
    goals_scored = models.IntegerField(default=0)
    goals_conceded = models.IntegerField(default=0)
    

    def __str__(self):
        return f"{self.participant.user.username} | {self.group_name} | {self.points} pts"


# ==========================================
# 3. FOOTBALL: THE MATCH OBJECT
# ==========================================
class FootballMatch(models.Model):
    """
    The actual 1v1 game. Handles both Group matches and Knockout brackets.
    """
    STAGE_CHOICES = [
        ('GROUP', 'Group Stage'),
        ('KNOCKOUT', 'Knockout Stage'),
    ]
    
    tournament = models.ForeignKey('Tournament', on_delete=models.CASCADE, related_name='football_matches')
    stage = models.CharField(max_length=20, choices=STAGE_CHOICES)
    round_name = models.CharField(max_length=50) # e.g., 'Group A' or 'Quarter-Final'

    match_number = models.IntegerField(null= True, blank= True)
    
    # The two players facing off
    player_1 = models.ForeignKey(Participant, related_name='matches_as_p1', null=True, blank=True, on_delete=models.SET_NULL)
    player_2 = models.ForeignKey(Participant, related_name='matches_as_p2', null=True, blank=True, on_delete=models.SET_NULL)
    
    # The result
    p1_score = models.IntegerField(default=0, null=True, blank=True)
    p2_score = models.IntegerField(default=0, null=True, blank=True)
    winner = models.ForeignKey(Participant, related_name='matches_won', null=True, blank=True, on_delete=models.SET_NULL)
    
    # For knockouts: Tells the winner which match they go to next
    next_match = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True)
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.round_name}: {self.player_1} vs {self.player_2}"


# ==========================================
# 4. BATTLE ROYALE: THE LOBBY
# ==========================================
class BattleRoyaleMatch(models.Model):
    """
    The overall 100-player game instance (e.g., 'Match 1 of 3').
    """
    tournament = models.ForeignKey('Tournament', on_delete=models.CASCADE, related_name='br_matches')
    match_number = models.IntegerField(default=1) 
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.tournament.title} - Match #{self.match_number}"


# ==========================================
# 5. BATTLE ROYALE: PLAYER RESULTS
# ==========================================
class BattleRoyaleResult(models.Model):
    """
    The individual performance of a player inside a specific BR Lobby.
    """
    match = models.ForeignKey(BattleRoyaleMatch, on_delete=models.CASCADE, related_name='results')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='br_results')
    
    kills = models.IntegerField(default=0)
    rank = models.IntegerField(null=True, blank=True) # 1st, 2nd, 100th, etc.
    total_points = models.IntegerField(default=0) # You can calculate this based on rank + kills

    def __str__(self):
        return f"{self.participant.user.username} | Rank: {self.rank} | Kills: {self.kills}"