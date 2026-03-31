from .world_cup import WorldCupEngine
from .battle_royale import BattleRoyaleEngine

def get_tournament_engine(tournament):
    if not tournament.tournament_type or not tournament.tournament_type.engine_code:
        raise ValueError('Tournament does not have a valid tournament_type or engine_code assigned to it')
    
    ENGINE_MAPPING = {
        'world_cup': WorldCupEngine,
        'battle_royale': BattleRoyaleEngine
    }

    engine_code = tournament.tournament_type.engine_code
    engine_class = ENGINE_MAPPING.get(engine_code)

    if not engine_class:
        raise ValueError(f"no engine found for format: {engine_code}")
    
    return engine_class(tournament)