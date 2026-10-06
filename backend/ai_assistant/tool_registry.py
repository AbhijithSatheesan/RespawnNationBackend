from .tools.tournament_tools import (
    get_tournament,
    list_tournaments,
    get_game_tournaments,
    get_my_tournaments,
)


TOOL_REGISTRY = {
    "get_tournament": get_tournament,
    "list_tournaments": list_tournaments,
    "get_game_tournaments": get_game_tournaments,
    "get_my_tournaments": get_my_tournaments,
}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_tournament",
            "description": (
                "Get summary information about one specific "
                "Respawn Nation tournament."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "tournament_id": {
                        "type": "integer",
                        "description": "The tournament ID."
                    }
                },
                "required": ["tournament_id"]
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "list_tournaments",
            "description": (
                "List Respawn Nation tournaments. "
                "Use this when the user asks for available, open, "
                "ongoing, current, past, completed, or all tournaments."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "status": {
                        "type": "string",
                        "enum": [
                            "REGISTRATION",
                            "GENERATING",
                            "LIVE",
                            "COMPLETED"
                        ],
                        "description": (
                            "Filter tournaments by status. "
                            "REGISTRATION means open/available for registration. "
                            "GENERATING means tournament generation is in progress. "
                            "LIVE means currently ongoing. "
                            "COMPLETED means past tournaments."
                        )
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "description": "Maximum number of tournaments to return."
                    }
                }
            }
        }
    },

    {
        "type": "function",
        "function": {
            "name": "get_game_tournaments",
            "description": (
                "List tournaments belonging to a specific game."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "game_id": {
                        "type": "integer",
                        "description": "The game ID."
                    },
                    "status": {
                        "type": "string",
                        "enum": [
                            "REGISTRATION",
                            "GENERATING",
                            "LIVE",
                            "COMPLETED"
                        ]
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20
                    }
                },
                "required": ["game_id"]
            }
        }
    }
]