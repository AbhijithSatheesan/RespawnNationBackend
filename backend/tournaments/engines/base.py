

class BaseTournamentEngine:
    def __init__(self, tournament):
        self.tournament = tournament

    def generate_initial_matches(self):
        raise NotImplementedError('Subclasses must implement generate_initial_matches()')
    
    def generate_knockout_matches(self):
        raise NotImplementedError('Subclasses must implement generate_knockout_matches()')