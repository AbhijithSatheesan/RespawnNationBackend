import random
from itertools import combinations
from django.db.models import Max, F
from ..models import FootballStanding, FootballMatch # Use '..' to go up one folder to your models
from .base import BaseTournamentEngine

class WorldCupEngine(BaseTournamentEngine):

    def generate_initial_matches(self):
        # 1. GENERATE GROUP STAGE
        participants = list(self.tournament.participants.all())
        num_players = len(participants)
        
        if num_players >= 16:
            num_groups = 8
        elif num_players >= 8:
            num_groups = 4
        elif num_players >= 4:
            num_groups = 2
        else:
            num_groups = 1

        random.shuffle(participants)
        group_names = [f"Group {chr(65+i)}" for i in range(num_groups)]
        groups = {name: [] for name in group_names}

        for index, participant in enumerate(participants):
            assigned_group = group_names[index % num_groups]
            groups[assigned_group].append(participant)

            FootballStanding.objects.create(
                participant=participant,
                group_name=assigned_group
            )

        match_counter = 1 
        for group_name, members in groups.items():
            pairings = list(combinations(members, 2))

            for player1, player2 in pairings:
                FootballMatch.objects.create(
                    tournament=self.tournament,
                    stage='GROUP',
                    round_name=group_name,
                    match_number=match_counter, 
                    player_1=player1,
                    player_2=player2
                )
                match_counter += 1

        self.tournament.status = 'LIVE'
        self.tournament.save()
        return True

    def generate_knockouts(self):
        # 2. GENERATE KNOCKOUT STAGE
        if FootballMatch.objects.filter(tournament=self.tournament, stage='KNOCKOUT').exists():
            raise Exception('Knockouts for this tournament already made')
        
        highest_match = FootballMatch.objects.filter(tournament=self.tournament).aggregate(Max('match_number'))
        match_counter = (highest_match['match_number__max'] or 0) + 1

        standings = FootballStanding.objects.filter(participant__tournament=self.tournament).annotate(
            goal_difference=F('goals_scored') - F('goals_conceded')
        ).order_by('group_name', '-points', '-goal_difference','-goals_scored')

        total_participants = self.tournament.participants.count()
        advancing_limit = 2 if total_participants == 32 else 1
        
        advancing_players = {}
        for standing in standings:
            group = standing.group_name
            if group not in advancing_players:
                advancing_players[group] = []

            if len(advancing_players[group]) < advancing_limit:
                advancing_players[group].append(standing.participant)

        num_groups = len(advancing_players)
        total_advancing = sum(len(players) for players in advancing_players.values())

        # --- THE WORLD CUP FORMAT ---
        if total_advancing == 16 and num_groups == 8:
            final = FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Final', match_number=match_counter+14)
            sf1 = FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Semi-Final', match_number=match_counter+12, next_match=final)
            sf2 = FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Semi-Final', match_number=match_counter+13, next_match=final)

            qf1 = FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Quarter-Final', match_number=match_counter+8, next_match=sf1)
            qf2 = FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Quarter-Final', match_number=match_counter+9, next_match=sf1)
            qf3 = FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Quarter-Final', match_number=match_counter+10, next_match=sf2)
            qf4 = FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Quarter-Final', match_number=match_counter+11, next_match=sf2)

            # Round of 16 - Left Side
            FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Round of 16', match_number=match_counter,   player_1=advancing_players['Group A'][0], player_2=advancing_players['Group B'][1], next_match=qf1)
            FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Round of 16', match_number=match_counter+1, player_1=advancing_players['Group C'][0], player_2=advancing_players['Group D'][1], next_match=qf1)
            FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Round of 16', match_number=match_counter+2, player_1=advancing_players['Group E'][0], player_2=advancing_players['Group F'][1], next_match=qf2)
            FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Round of 16', match_number=match_counter+3, player_1=advancing_players['Group G'][0], player_2=advancing_players['Group H'][1], next_match=qf2)
            
            # Round of 16 - Right Side
            FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Round of 16', match_number=match_counter+4, player_1=advancing_players['Group B'][0], player_2=advancing_players['Group A'][1], next_match=qf3)
            FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Round of 16', match_number=match_counter+5, player_1=advancing_players['Group D'][0], player_2=advancing_players['Group C'][1], next_match=qf3)
            FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Round of 16', match_number=match_counter+6, player_1=advancing_players['Group F'][0], player_2=advancing_players['Group E'][1], next_match=qf4)
            FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Round of 16', match_number=match_counter+7, player_1=advancing_players['Group H'][0], player_2=advancing_players['Group G'][1], next_match=qf4)

        # --- 8 GROUPS (Top 1) -> QF ---
        elif total_advancing == 8 and num_groups == 8:
            final = FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Final', match_number=match_counter+6)
            sf1 = FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Semi-Final', match_number=match_counter+4, next_match=final)
            sf2 = FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Semi-Final', match_number=match_counter+5, next_match=final)

            FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Quarter-Final', match_number=match_counter, player_1=advancing_players['Group A'][0], player_2=advancing_players['Group B'][0], next_match=sf1)
            FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Quarter-Final', match_number=match_counter+1, player_1=advancing_players['Group C'][0], player_2=advancing_players['Group D'][0], next_match=sf1)
            FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Quarter-Final', match_number=match_counter+2, player_1=advancing_players['Group E'][0], player_2=advancing_players['Group F'][0], next_match=sf2)
            FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Quarter-Final', match_number=match_counter+3, player_1=advancing_players['Group G'][0], player_2=advancing_players['Group H'][0], next_match=sf2)

        # --- 4 GROUPS -> SF ---
        elif total_advancing == 4 and num_groups == 4:
            final = FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Final', match_number=match_counter+2)
            FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Semi-Final', match_number=match_counter, player_1=advancing_players['Group A'][0], player_2=advancing_players['Group B'][0], next_match=final)
            FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Semi-Final', match_number=match_counter+1, player_1=advancing_players['Group C'][0], player_2=advancing_players['Group D'][0], next_match=final)

        # --- 2 GROUPS -> FINAL ---
        elif total_advancing == 2 and num_groups == 2:
            FootballMatch.objects.create(tournament=self.tournament, stage='KNOCKOUT', round_name='Final', match_number=match_counter, player_1=advancing_players['Group A'][0], player_2=advancing_players['Group B'][0])

        else:
            raise Exception(f"Invalid setup for knockouts. Groups: {num_groups}, Advancing: {total_advancing}")

        return True
    


    def submit_score(self, user, data, files):
        # We expect the React frontend to send the match_id
        match_id = data.get('match_id')
        match = FootballMatch.objects.get(id=match_id, tournament=self.tournament)

        # Ensure the match is actually active before accepting scores
        if match.status not in ['SCHEDULED', 'LIVE', 'DISPUTED']:
            raise ValueError(f"Cannot submit scores. Match status is {match.status}.")

        # Figure out if the uploading user is Player 1 or Player 2
        if match.player_1 and match.player_1.user == user:
            match.p1_score = data.get('score', 0)
            if 'proof_image' in files:
                match.player_1_proof = files['proof_image']
        
        elif match.player_2 and match.player_2.user == user:
            match.p2_score = data.get('score', 0)
            if 'proof_image' in files:
                match.player_2_proof = files['proof_image']
        else:
            raise ValueError("You are not authorized to submit scores for this match.")

        # Flag the match for admin review!
        match.status = 'AWAITING_REVIEW'
        match.save()
        
        return {"match_id": match.id, "status": match.status}
    


    def get_user_matches(self, user):
        from django.db.models import Q
        from ..models import FootballMatch
        
        # Find matches where this user is either player 1 or player 2
        matches = FootballMatch.objects.filter(
            tournament=self.tournament
        ).filter(Q(player_1__user=user) | Q(player_2__user=user)).order_by('-id')

        data = []
        for m in matches:
            # Figure out who the opponent is
            is_p1 = m.player_1 and m.player_1.user == user
            opponent = m.player_2 if is_p1 else m.player_1
            opponent_name = opponent.user.username if opponent and opponent.user else "TBD"
            
            data.append({
                "match_id": m.id,
                "round_name": m.round_name,
                "opponent": opponent_name,
                "status": m.status,
                "my_score": m.p1_score if is_p1 else m.p2_score,
                "requires_proof": self.tournament.requires_player_proof,
                "type": "1v1"
            })
        return data