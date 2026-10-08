import logging

from django.db.models import Q

from games.models import Games

from .tool_result import ToolResult


logger = logging.getLogger(__name__)


def search_games(
    query: str | None = None,
    category: str | None = None,
    limit: int = 10,
) -> ToolResult:
    """
    Search games by name, tags, or category.

    Read-only.
    """

    limit = max(1, min(limit, 20))

    query = (query or "").strip()
    category = (category or "").strip()

    if not query and not category:
        return ToolResult.fail(
            code="GAME_SEARCH_QUERY_REQUIRED",
            message="A game name, tag, or category is required.",
            retryable=False,
        )

    try:
        queryset = Games.objects.all()

        # --------------------------------------------------
        # Search by name, tags, or category
        # --------------------------------------------------

        if query:
            queryset = queryset.filter(
                Q(name__icontains=query)
                | Q(tags__icontains=query)
                | Q(categories__name__icontains=query)
            )

        # --------------------------------------------------
        # Optional category filter
        # --------------------------------------------------

        if category:
            queryset = queryset.filter(
                categories__name__icontains=category
            )

        # Prevent duplicate games caused by ManyToMany join
        games = (
            queryset
            .distinct()
            .prefetch_related("categories")
            .order_by("name")[:limit]
        )

        results = []

        for game in games:
            results.append({
                "id": game.id,
                "name": game.name,
                "categories": [
                    category.name
                    for category in game.categories.all()
                ],
                "tags": game.tags,
                "release_year": game.release_year,
                "rating": game.rating,
            })

        return ToolResult.ok({
            "games": results,
            "count": len(results),
        })

    except Exception:
        logger.exception(
            "Failed to search games",
            extra={
                "query": query,
                "category": category,
                "limit": limit,
            },
        )

        return ToolResult.fail(
            code="GAME_SEARCH_FAILED",
            message="Unable to search games right now.",
            retryable=True,
        )