from django.db import models
from django.db.models import Sum
from games.models import Games

# Create your models here.

from django.db import models
from django.conf import settings



class TournamentType(models.Model):
    name = models.CharField(max_length= 100, unique= True)
    engine_code = models.CharField(max_length= 50, unique= True, null= True)
    description = models.TextField(blank= True, null= True)
    format_overlay = models.ImageField(upload_to='tournaments/overlays', null= True, blank= True)

    def __str__(self):
        return self.name
    
    # when creating new TournamentType, give engine code, create a file with same engine code in tournaments/engine,
    #    write the new tournament logic in the file we created and add it to the factory.py to connect it with the tournament

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
    tournament_type = models.ForeignKey(TournamentType, on_delete= models.SET_NULL, null= True, blank= True, related_name= 'Tournaments')
    max_players = models.IntegerField(default=32)
    created_at = models.DateTimeField(auto_now_add= True)
    registration_deadline = models.DateTimeField()
    winner = models.ForeignKey('Participant', related_name= 'tournaments_won', on_delete= models.SET_NULL, null= True, blank= True )
    runner_up = models.ForeignKey('Participant', related_name= 'tournaments_runner_up', on_delete= models.SET_NULL, null= True, blank= True)

    custom_banner = models.ImageField(upload_to='tournaments/custom_banner', null= True, blank= True)

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
    game_id = models.CharField(max_length= 30, null= True, blank= True)
    
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
    next_match = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, related_name='previous_matches')
    is_completed = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.round_name}: {self.player_1} vs {self.player_2}"









class BattleRoyaleMatch(models.Model):
    tournament = models.ForeignKey('Tournament', on_delete=models.CASCADE, related_name='br_matches')
    match_number = models.IntegerField(default=1) 
    is_completed = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs) # Save the match first
        
        # AUTOMATIC WINNER CROWNING
        if self.is_completed:
            tourney = self.tournament
            
            # Check if ALL matches in this tournament are completed
            incomplete_matches = tourney.br_matches.filter(is_completed=False).exists()
            
            if not incomplete_matches:
                # 1. Change tournament status to completed
                tourney.status = 'COMPLETED'
                
                # 2. Find the player with the highest overall points
                top_player = BattleRoyaleResult.objects.filter(match__tournament=tourney)\
                    .values('participant')\
                    .annotate(overall_pts=Sum('total_points'))\
                    .order_by('-overall_pts').first()
                
                if top_player:
                    # 3. Crown them the winner!
                    tourney.winner_id = top_player['participant']
                
                tourney.save()

    def __str__(self):
        return f"{self.tournament.title} - Match #{self.match_number}"
    


    

class BattleRoyaleResult(models.Model):
    match = models.ForeignKey(BattleRoyaleMatch, on_delete=models.CASCADE, related_name='results')
    participant = models.ForeignKey(Participant, on_delete=models.CASCADE, related_name='br_results')
    
    kills = models.IntegerField(default=0)
    rank = models.IntegerField(null=True, blank=True)
    total_points = models.IntegerField(default=0)

    def save(self, *args, **kwargs):
        # AUTOMATIC POINT CALCULATION
        # Example: 1st place = 100pts, 2nd = 80pts, 3rd = 60pts. Plus 10 points per kill.
        placement_points = {1: 100, 2: 80, 3: 60}
        
        base_points = 0
        if self.rank in placement_points:
            base_points = placement_points[self.rank]
            
        self.total_points = base_points + (self.kills * 10)
        
        super().save(*args, **kwargs) # Save the calculated points to the database

    def __str__(self):
        return f"{self.participant.user.username} | Rank: {self.rank} | Kills: {self.kills}"