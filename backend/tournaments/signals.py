from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import FootballMatch, FootballStanding


@receiver(post_save, sender= FootballMatch) # when ever a save occurs in FootballMatch models, this function gets called
def update_group_standing(sender, instance, created, **kwargs):

    # Group Stage Logic
    if instance.is_completed and instance.stage == 'GROUP':

        p1 = instance.player_1
        p2 = instance.player_2

        # Should check if p1 and p2 actually exists
        if not p1 or not p2:
            return
        
        p1_standing = FootballStanding.objects.get(participant = p1)
        p2_standing = FootballStanding.objects.get(participant = p2)

        # Update mathces played and goals scored
        p1_standing.matches_played += 1
        p1_standing.goals_scored += instance.p1_score
        p1_standing.goals_conceded += instance.p2_score

        p2_standing.matches_played += 1
        p2_standing.goals_scored += instance.p2_score
        p2_standing.goals_conceded += instance.p1_score

        # Determine win lose and draw
        if instance.p1_score > instance.p2_score:
            p1_standing.points += 3
            FootballMatch.objects.filter(pk = instance.pk).update(winner = p1)

        elif instance.p2_score > instance.p1_score:
            p2_standing.points += 3
            FootballMatch.objects.filter(pk = instance.pk).update(winner = p2)

        else:
            p1_standing.points += 1
            p2_standing.points += 1

        p1_standing.save()
        p2_standing.save()





    # NOW TO KNOCKOUTSTAGE
    if instance.is_completed and instance.stage == 'KNOCKOUT':
        winner = None
        loser = None

        # Determine winner and loser
        if instance.p1_score > instance.p2_score:
            winner = instance.player_1
            loser = instance.player_2
        elif instance.p2_score > instance.p1_score:
            winner = instance.player_2
            loser = instance.player_1

        # now update the winner in FootBallMatch object
        if winner:
            FootballMatch.objects.filter(pk = instance.pk).update(winner = winner)

            # if the match was final then,
            if instance.round_name == 'Final':
                tournament = instance.tournament
                tournament.winner = winner
                tournament.runner_up = loser
                tournament.status = 'COMPLETED'
                tournament.save()
    
            # if it was not final, then normal advancement
            elif instance.next_match:
                next_match = instance.next_match
                # drop hem to empth slots
                if next_match.player_1 is None:
                    next_match.player_1 = winner
                elif next_match.player_2 is None:
                    next_match.player_2 = winner
                next_match.save()
    
    





