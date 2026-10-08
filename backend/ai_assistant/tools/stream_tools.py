import logging

from django.db.models import Q

from streams.models import Stream
from .tool_result import ToolResult

logger = logging.getLogger(__name__)


def _stream_summary(stream: Stream) -> dict:
    """
    Convert a Stream model into a small, AI-safe representation.

    Never expose:
    - stream_key
    - cloudflare_id
    - raw model data
    """

    return {
        "id": stream.id,
        "title": stream.title,
        "streamer": (
            stream.user.username
            if stream.user
            else None
        ),
        "game": (
            stream.game.name
            if stream.game
            else None
        ),
        "tournament": (
            stream.active_tournament.title
            if stream.active_tournament
            else None
        ),
        "stream_type": stream.stream_type,
        "description": stream.description,
        "thumbnail": (
            stream.thumbnail.url
            if stream.thumbnail
            else None
        ),
        "watch_url": stream.hls_url,
        "is_live": stream.is_live,
    }


def list_live_streams(
    game_id: int | None = None,
    tournament_id: int | None = None,
    query: str | None = None,
    limit: int = 10,
) -> ToolResult:

    limit = max(1, min(limit, 20))

    try:
        queryset = (
            Stream.objects
            .filter(is_live=True)
            .select_related(
                "user",
                "game",
                "active_tournament",
            )
        )

        if game_id is not None:
            queryset = queryset.filter(game_id=game_id)

        if tournament_id is not None:
            queryset = queryset.filter(
                active_tournament_id=tournament_id
            )

        if query:
            query = query.strip()

            queryset = queryset.filter(
                Q(title__icontains=query)
                | Q(description__icontains=query)
                | Q(user__username__icontains=query)
                | Q(game__name__icontains=query)
                | Q(active_tournament__title__icontains=query)
            )

        streams = queryset.order_by("-created_at")[:limit]

        data = [
            _stream_summary(stream)
            for stream in streams
        ]

        return ToolResult.ok({
            "streams": data,
            "count": len(data),
        })

    except Exception:
        logger.exception(
            "Failed to list live streams",
            extra={
                "game_id": game_id,
                "tournament_id": tournament_id,
                "query": query,
                "limit": limit,
            },
        )

        return ToolResult.fail(
            code="LIVE_STREAMS_FETCH_FAILED",
            message="Unable to retrieve live streams right now.",
            retryable=True,
        )


def get_stream(stream_id: int) -> ToolResult:

    try:
        stream = (
            Stream.objects
            .filter(
                id=stream_id,
                is_live=True,
            )
            .select_related(
                "user",
                "game",
                "active_tournament",
            )
            .first()
        )

        if not stream:
            return ToolResult.fail(
                code="STREAM_NOT_FOUND",
                message="The requested live stream does not exist.",
                retryable=False,
            )

        return ToolResult.ok(
            _stream_summary(stream)
        )

    except Exception:
        logger.exception(
            "Failed to fetch stream",
            extra={
                "stream_id": stream_id,
            },
        )

        return ToolResult.fail(
            code="STREAM_FETCH_FAILED",
            message="Unable to retrieve stream information right now.",
            retryable=True,
        )