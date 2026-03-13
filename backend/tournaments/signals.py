from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import FootballMatch, FootballStanding

@receiver(post_save, sender=FootballMatch)
def update_group_standings(sender, instance, created, **kwargs):
    """
    This function fires automatically EVERY time a FootballMatch is saved.
    """
    
    # 1. THE GUARD CLAUSE: Only run the math if the match is officially completed
    # and it is a Group Stage match (Knockouts don't have standings tables).
    if instance.is_completed and instance.stage == 'GROUP':
        
        p1 = instance.player_1
        p2 = instance.player_2

        # Safety check: Ensure both players actually exist
        if not p1 or not p2:
            return

        # 2. Fetch their "Scorecards" from the database
        p1_standing = FootballStanding.objects.get(participant=p1)
        p2_standing = FootballStanding.objects.get(participant=p2)

        # 3. Update the basic stats (Matches Played & Goals)
        p1_standing.matches_played += 1
        p1_standing.goals_scored += instance.p1_score
        p1_standing.goals_conceded += instance.p2_score
        
        p2_standing.matches_played += 1
        p2_standing.goals_scored += instance.p2_score
        p2_standing.goals_conceded += instance.p1_score

        # 4. Calculate Points (3 for Win, 1 for Draw, 0 for Loss)
        if instance.p1_score > instance.p2_score:
            # Player 1 Wins
            p1_standing.points += 3
            # Quietly update the winner field on the match without triggering another save loop
            FootballMatch.objects.filter(pk=instance.pk).update(winner=p1)
            
        elif instance.p2_score > instance.p1_score:
            # Player 2 Wins
            p2_standing.points += 3
            FootballMatch.objects.filter(pk=instance.pk).update(winner=p2)
            
        else:
            # It's a Draw
            p1_standing.points += 1
            p2_standing.points += 1

        # 5. Save the updated scorecards back to the database
        p1_standing.save()
        p2_standing.save()