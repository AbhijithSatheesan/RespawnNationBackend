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