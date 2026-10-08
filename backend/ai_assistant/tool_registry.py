from .tools.stream_tools import (
    list_live_streams,
    get_stream,
)

from .tools.game_tools import search_games
from .tools.tournament_tools import (
    get_tournament,
    list_tournaments,
    get_game_tournaments,
    get_my_tournaments,
)





TOOL_REGISTRY = {
    "search_games": search_games,
    "get_tournament": get_tournament,
    "list_tournaments": list_tournaments,
    "get_game_tournaments": get_game_tournaments,
    "get_my_tournaments": get_my_tournaments,
    "list_live_streams": list_live_streams,
    "get_stream": get_stream,
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
            "name": "search_games",
            "description": (
                "Search Respawn Nation games by game name, tags, or category. "
                "Use this when the user mentions a game by name instead of a database ID. "
                "Never ask the user for a game ID when the game can be resolved by name."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": (
                            "Game name, keyword, or tag to search for. "
                            "Examples: Efootball, football, multiplayer, battle royale."
                        ),
                    },
                    "category": {
                        "type": "string",
                        "description": (
                            "Optional game category to filter by. "
                            "Example: Sports."
                        ),
                    },
                    "limit": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "description": "Maximum number of games to return.",
                    },
                },
            },
        },
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
    },
    
    {
    "type": "function",
    "function": {
        "name": "list_live_streams",
        "description": (
            "List currently live streams on Respawn Nation. "
            "Can filter by game, tournament, streamer, title, "
            "or other related text."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "game_id": {
                    "type": "integer",
                    "description": (
                        "Internal game ID. Use search_games first "
                        "when the user names a game."
                    )
                },
                "tournament_id": {
                    "type": "integer",
                    "description": (
                        "Internal tournament ID when a specific "
                        "tournament's streams are requested."
                    )
                },
                "query": {
                    "type": "string",
                    "description": (
                        "Search text for stream title, description, "
                        "streamer username, game name, or tournament name."
                    )
                },
                "limit": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 20,
                    "description": (
                        "Maximum number of live streams to return."
                    )
                }
            }
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_stream",
        "description": (
            "Get information about one specific currently live "
            "Respawn Nation stream."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "stream_id": {
                    "type": "integer",
                    "description": "The internal stream ID."
                }
            },
            "required": ["stream_id"]
        }
    }
},
]