# tournaments/engines/points_race.py
from decimal import Decimal
from django.db import transaction

class PointsRaceEngine:
    def __init__(self, tournament):
        self.tournament = tournament

    def generate_initial_matches(self):
        """
        Generates initial arena round-robin or targeted match lobby schedules.
        Changes tournament status from 'GENERATING' to 'LIVE'.
        """
        with transaction.atomic():
            # 1. Fetch registered participants
            participants = list(self.tournament.participants.all())
            
            if len(participants) < 2:
                raise ValueError("Need at least 2 participants to generate matches.")

            # 2. Add your custom pairing/match creation logic here
            # e.g., create ArenaMatch or reuse generic match model

            # 3. Update status to LIVE
            self.tournament.status = 'LIVE'
            self.tournament.save()

    def generate_knockouts(self):
        """
        For points race, this might check who reached the target score (e.g. 50 pts)
        or advance top players to a Final Showdown.
        """
        pass