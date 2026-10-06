import logging

from tournaments.models import Tournament, Participant
from tournaments.serializers import (
    TournamentSerializer,
    TournamentDetailSerializer,
)

from .tool_result import ToolResult


logger = logging.getLogger(__name__)


VALID_TOURNAMENT_STATUSES = {
    "REGISTRATION",
    "GENERATING",
    "LIVE",
    "COMPLETED",
}


# GET A SPECIFIC TOURNAMENT

def get_tournament(tournament_id: int) -> ToolResult:
    """
    Retrieve details about a specific tournament.
    Read-only.
    """

    try:
        tournament = (
            Tournament.objects
            .select_related("game", "winner")
            .get(id=tournament_id)
        )


        data = TournamentDetailSerializer(tournament).data

        summary = {
            "id": data.get("id"),
            "name": data.get("title"),
            "game": data.get("game_name"),
            "status": data.get("status"),
            "format": data.get("type_name"),
            "prize_pool": data.get("current_prize_pool"),
            "registration_deadline": data.get("registration_deadline"),
            "winner": data.get("winner_name"),
        }

        return ToolResult.ok(summary)

      

    except Tournament.DoesNotExist:
        return ToolResult.fail(
            code="TOURNAMENT_NOT_FOUND",
            message="The requested tournament does not exist.",
            retryable=False,
        )

    except Exception:
        logger.exception(
            "Failed to fetch tournament",
            extra={
                "tournament_id": tournament_id,
            }
        )

        return ToolResult.fail(
            code="TOURNAMENT_FETCH_FAILED",
            message="Unable to retrieve tournament information right now.",
            retryable=True,
        )


# LIST TOURNAMENTS

def list_tournaments(
    status: str | None = None,
    limit: int = 10,
) -> ToolResult:
    """
    List tournaments, optionally filtered by status.
    Read-only.
    """

    limit = max(1, min(limit, 20))

    if status and status not in VALID_TOURNAMENT_STATUSES:
        return ToolResult.fail(
            code="INVALID_TOURNAMENT_STATUS",
            message="Invalid tournament status.",
            retryable=False,
        )

    try:
        queryset = (
            Tournament.objects
            .select_related("game")
        )

        if status:
            queryset = queryset.filter(status=status)

        tournaments = (
            queryset
            .order_by("registration_deadline")[:limit]
        )

        data = TournamentSerializer(
            tournaments,
            many=True
        ).data

        return ToolResult.ok({
            "tournaments": data,
            "count": len(data),
        })

    except Exception:
        logger.exception(
            "Failed to list tournaments",
            extra={
                "status": status,
                "limit": limit,
            }
        )

        return ToolResult.fail(
            code="TOURNAMENT_LIST_FAILED",
            message="Unable to retrieve tournaments right now.",
            retryable=True,
        )


# GET TOURNAMENTS BASED ON GAME

def get_game_tournaments(
    game_id: int,
    status: str | None = None,
    limit: int = 10,
) -> ToolResult:

    limit = max(1, min(limit, 20))

    if status and status not in VALID_TOURNAMENT_STATUSES:
        return ToolResult.fail(
            code="INVALID_TOURNAMENT_STATUS",
            message="Invalid tournament status.",
            retryable=False,
        )

    try:
        queryset = (
            Tournament.objects
            .filter(game_id=game_id)
            .select_related("game")
        )

        if status:
            queryset = queryset.filter(status=status)

        tournaments = (
            queryset
            .order_by("-created_at")[:limit]
        )

        data = TournamentSerializer(
            tournaments,
            many=True
        ).data

        return ToolResult.ok({
            "game_id": game_id,
            "tournaments": data,
            "count": len(data),
        })

    except Exception:
        logger.exception(
            "Failed to fetch game tournaments",
            extra={
                "game_id": game_id,
                "status": status,
                "limit": limit,
            }
        )

        return ToolResult.fail(
            code="GAME_TOURNAMENTS_FETCH_FAILED",
            message="Unable to retrieve tournaments for this game.",
            retryable=True,
        )


# GET USER'S TOURNAMENT HISTORY

def get_my_tournaments(user) -> ToolResult:

    try:
        participants = (
            Participant.objects
            .filter(user=user)
            .select_related("tournament", "tournament__game")
            .order_by("-tournament__created_at")
        )

        tournaments = []

        for participant in participants:
            tournament = participant.tournament

            tournaments.append({
                "id": tournament.id,
                "title": tournament.title,
                "status": tournament.status,
                "game": (
                    tournament.game.name
                    if tournament.game
                    else None
                ),
                "participant_id": participant.id,
            })

        return ToolResult.ok({
            "tournaments": tournaments
        })

    except Exception:
        logger.exception(
            "Failed to fetch user's tournament history",
            extra={
                "user_id": user.id,
            }
        )

        return ToolResult.fail(
            code="USER_TOURNAMENTS_FETCH_FAILED",
            message="Unable to retrieve your tournament history.",
            retryable=True,
        )