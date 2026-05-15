
import random
from itertools import combinations
from django.db.models import Max,F
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








# now generate knockout matches

def generate_knockout_stage(tournament):

    # should check weather tournament knockouts already made or not
    if FootballMatch.objects.filter(tournament = tournament, stage = 'KNOCKOUT').exists():
        raise Exception('Knockouts for this tournament already made')
    
    # The match number of the knockout matches should start right after the number of group mathces
    highest_match = FootballMatch.objects.filter(tournament= tournament).aggregate(Max('match_number'))
    match_counter = (highest_match['match_number__max'] or 0) + 1


    # now order all the standings
    standings = FootballStanding.objects.filter(participant__tournament = tournament).annotate(
        goal_difference = F('goals_scored') -F('goals_conceded')
    ).order_by('group_name', '-points', '-goal_difference')

    # if there is exactly 32 players, then round of 16 will be there(top 2 players from each group advances), or else top 1 advances
    total_participants = tournament.participants.count()
    advancing_limit = 2 if total_participants == 32 else 1
    
    # make a dictionary with key as groupname
    advancing_players = {}
    for standing in standings:
        group = standing.group_name
        if group not in advancing_players:
            advancing_players[group] = []

        # fill the groups with participants in advancing players dictionary accoriding to the number of advancing limit allowed in each group
        if len(advancing_players[group]) < advancing_limit:
            advancing_players[group].append(standing.participant)

    num_groups = len(advancing_players)
    total_advancing = sum(len(players) for players in advancing_players.values())


    # --- THE WORLD CUP FORMAT (32 Players -> 8 Groups -> Top 2 Advance -> Round of 16) ---
    if total_advancing == 16 and num_groups == 8:
        # Create empty future matches backward from the Final
        final = FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Final', match_number=match_counter+14)
        
        sf1 = FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Semi-Final', match_number=match_counter+12, next_match=final)
        sf2 = FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Semi-Final', match_number=match_counter+13, next_match=final)

        qf1 = FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Quarter-Final', match_number=match_counter+8, next_match=sf1)
        qf2 = FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Quarter-Final', match_number=match_counter+9, next_match=sf1)
        qf3 = FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Quarter-Final', match_number=match_counter+10, next_match=sf2)
        qf4 = FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Quarter-Final', match_number=match_counter+11, next_match=sf2)

        # Round of 16 - Left Side of Bracket (A1vB2, C1vD2, E1vF2, G1vH2)
        FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Round of 16', match_number=match_counter,   player_1=advancing_players['Group A'][0], player_2=advancing_players['Group B'][1], next_match=qf1)
        FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Round of 16', match_number=match_counter+1, player_1=advancing_players['Group C'][0], player_2=advancing_players['Group D'][1], next_match=qf1)
        FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Round of 16', match_number=match_counter+2, player_1=advancing_players['Group E'][0], player_2=advancing_players['Group F'][1], next_match=qf2)
        FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Round of 16', match_number=match_counter+3, player_1=advancing_players['Group G'][0], player_2=advancing_players['Group H'][1], next_match=qf2)
        
        # Round of 16 - Right Side of Bracket (B1vA2, D1vC2, F1vE2, H1vG2)
        FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Round of 16', match_number=match_counter+4, player_1=advancing_players['Group B'][0], player_2=advancing_players['Group A'][1], next_match=qf3)
        FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Round of 16', match_number=match_counter+5, player_1=advancing_players['Group D'][0], player_2=advancing_players['Group C'][1], next_match=qf3)
        FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Round of 16', match_number=match_counter+6, player_1=advancing_players['Group F'][0], player_2=advancing_players['Group E'][1], next_match=qf4)
        FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Round of 16', match_number=match_counter+7, player_1=advancing_players['Group H'][0], player_2=advancing_players['Group G'][1], next_match=qf4)

    # --- 8 GROUPS (Top 1 Advance) -> DIRECT QUARTER-FINALS ---
    elif total_advancing == 8 and num_groups == 8:
        final = FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Final', match_number=match_counter+6)
        
        sf1 = FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Semi-Final', match_number=match_counter+4, next_match=final)
        sf2 = FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Semi-Final', match_number=match_counter+5, next_match=final)

        FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Quarter-Final', match_number=match_counter, player_1=advancing_players['Group A'][0], player_2=advancing_players['Group B'][0], next_match=sf1)
        FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Quarter-Final', match_number=match_counter+1, player_1=advancing_players['Group C'][0], player_2=advancing_players['Group D'][0], next_match=sf1)
        FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Quarter-Final', match_number=match_counter+2, player_1=advancing_players['Group E'][0], player_2=advancing_players['Group F'][0], next_match=sf2)
        FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Quarter-Final', match_number=match_counter+3, player_1=advancing_players['Group G'][0], player_2=advancing_players['Group H'][0], next_match=sf2)

    # --- 4 GROUPS (e.g., 12 or 13 teams) -> DIRECT SEMI-FINALS ---
    elif total_advancing == 4 and num_groups == 4:
        final = FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Final', match_number=match_counter+2)
        
        FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Semi-Final', match_number=match_counter, player_1=advancing_players['Group A'][0], player_2=advancing_players['Group B'][0], next_match=final)
        FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Semi-Final', match_number=match_counter+1, player_1=advancing_players['Group C'][0], player_2=advancing_players['Group D'][0], next_match=final)

    # --- 2 GROUPS (Under 8 teams) -> DIRECT FINAL ---
    elif total_advancing == 2 and num_groups == 2:
        FootballMatch.objects.create(tournament=tournament, stage='KNOCKOUT', round_name='Final', match_number=match_counter, player_1=advancing_players['Group A'][0], player_2=advancing_players['Group B'][0])

    else:
        raise Exception(f"Tournament has an invalid setup for knockouts. Groups: {num_groups}, Advancing: {total_advancing}")

    return True











