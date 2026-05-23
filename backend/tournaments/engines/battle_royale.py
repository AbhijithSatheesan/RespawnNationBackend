from ..models import BattleRoyaleMatch
from .base import BaseTournamentEngine

class BattleRoyaleEngine(BaseTournamentEngine):

    def generate_initial_matches(self):
        # This creates a single lobby match for all players
        BattleRoyaleMatch.objects.create(
            tournament = self.tournament,
            match_number = 1
        )
        self.tournament.status = 'LIVE'
        self.tournament.save()
        return True
    
    def generate_knockout_matches(self):
        # since battle royale does not have a knockout matches, we may raise an error if accedently raises
        raise ValueError('There is no knockouts for battleroyale')
    

    def submit_score(self, user, data, files):
        match_id = data.get('match_id')
        
        # 1. Find the specific result row for this participant in this match
        from ..models import Participant, BattleRoyaleResult
        participant = Participant.objects.get(tournament=self.tournament, user=user)
        result = BattleRoyaleResult.objects.get(match_id=match_id, participant=participant)

        # 2. Update stats and image
        result.kills = data.get('kills', result.kills)
        result.rank = data.get('rank', result.rank)
        
        if 'proof_image' in files:
            result.screenshot_proof = files['proof_image']
            
        result.save()

        # 3. If the match is still LIVE, flag it so the admin knows scores are coming in
        match = result.match
        if match.status == 'LIVE':
            match.status = 'AWAITING_REVIEW'
            match.save()

        return {"result_id": result.id, "kills": result.kills, "rank": result.rank}
    




    def get_user_matches(self, user):
        from ..models import BattleRoyaleResult
        
        # Find the result rows for this specific user
        results = BattleRoyaleResult.objects.filter(
            match__tournament=self.tournament,
            participant__user=user
        ).order_by('-match__match_number')

        data = []
        for r in results:
            data.append({
                "match_id": r.match.id,
                "match_number": r.match.match_number,
                "round_name": f"Match #{r.match.match_number}",
                "status": r.match.status,
                "kills": r.kills,
                "rank": r.rank,
                "requires_proof": self.tournament.requires_player_proof,
                "type": "br"
            })
        return data
    







    