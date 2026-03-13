
import random
from itertools import combinations
from .models import Tournament, FootballStanding, FootballMatch

def generate_football_group_stage(tournament):
    participants = list(tournament.participants.all())
    num_players = len(participants)
    
    # 1 grouping in a way so that no more than 4 players in a group or else there will be too much group matches
    if num_players >= 16:
        num_groups = 8
    elif num_players >= 8:
        num_groups = 4
    elif num_players >= 4:
        num_groups = 2
    else:
        num_groups = 1

    # Shuffle so registration wonlt descide the groups
    random.shuffle(participants)

    # 2  assign group names to the groups (chr 65 is A, chr 66 is B)
    group_names = [f"Group {chr(65+i)}" for i in range(num_groups)]
    groups = {name: [] for name in group_names}

    #3 add players to group in round robin way
    for index, participant in enumerate(participants):
        assigned_group = group_names[index % num_groups]
        groups[assigned_group].append(participant)

        # Create the Standings Scorecard
        FootballStanding.objects.create(
            participant=participant,
            group_name=assigned_group
        )

    # 4 Generate the Matches
    match_counter = 1 
    
    for group_name, members in groups.items():
        pairings = list(combinations(members, 2))

        for player1, player2 in pairings:
            FootballMatch.objects.create(
                tournament=tournament,
                stage='GROUP',
                round_name=group_name,
                match_number=match_counter, # <--- ASSIGN THE NUMBER
                player_1=player1,
                player_2=player2
            )
            match_counter += 1 # <--- INCREASE THE COUNTER FOR THE NEXT MATCH

    # 5 Last changes and save
    tournament.status = 'LIVE'
    tournament.save()
    
    return True