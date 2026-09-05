from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from .models import GameCategory, Games


class GamesViewsTests(APITestCase):

    def setUp(self):
        # Always clear Redis cache before each test
        cache.clear()

        # Required base categories (browse_games expects "Trending" and "Top Rated")
        self.trending_category = GameCategory.objects.create(
            name="Trending", main_category=True
        )
        self.top_rated_category = GameCategory.objects.create(
            name="Top Rated", main_category=False
        )
        self.action_category = GameCategory.objects.create(
            name="Action", main_category=True
        )

        # Create test games
        self.game1 = Games.objects.create(name="Tekken 8")
        self.game2 = Games.objects.create(name="Elden Ring")

        # Associate games with categories
        self.trending_category.games.add(self.game1)
        self.top_rated_category.games.add(self.game2)
        self.action_category.games.add(self.game1)

    # -------------------------------------------------------------------------
    # 1. BROWSE GAMES & REDIS CACHING
    # -------------------------------------------------------------------------
    def test_browse_games_cache_hit_and_miss(self):
        """Verify feed fetches from DB on miss, writes to Redis, and serves from cache on hit."""
        url = reverse("browse_games")
        cache_key = "browse_games_feed"

        # 1. Cache starts empty
        self.assertIsNone(cache.get(cache_key))

        # 2. First request -> DB Fetch & Cache Set
        response1 = self.client.get(url)
        self.assertEqual(response1.status_code, status.HTTP_200_OK)
        self.assertIn("Trending_games", response1.data)
        self.assertIsNotNone(cache.get(cache_key))

        # 3. Second request -> Served directly from Redis cache
        cached_payload = cache.get(cache_key)
        response2 = self.client.get(url)
        self.assertEqual(response2.status_code, status.HTTP_200_OK)
        self.assertEqual(response2.data, cached_payload)

    def test_browse_games_404_when_required_category_missing(self):
        """Verify 404 if 'Trending' or 'Top Rated' categories do not exist in DB."""
        self.trending_category.delete()
        url = reverse("browse_games")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -------------------------------------------------------------------------
    # 2. SEARCH GAMES
    # -------------------------------------------------------------------------
    def test_search_games_with_query(self):
        """Verify search returns matching games for case-insensitive query."""
        url = reverse("search-games")
        response = self.client.get(url, {"q": "tekken"})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["name"], "Tekken 8")

    def test_search_games_empty_query(self):
        """Verify search returns an empty array when query parameter is blank."""
        url = reverse("search-games")
        response = self.client.get(url, {"q": ""})

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data, [])

    # -------------------------------------------------------------------------
    # 3. TRENDING GAME
    # -------------------------------------------------------------------------
    def test_trending_game_returns_random_item(self):
        """Verify endpoint returns a valid random game from Trending category."""
        url = reverse("trending_game")
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("trending_game", response.data)
        self.assertEqual(response.data["trending_game"]["name"], "Tekken 8")

    def test_trending_game_none_when_empty(self):
        """Verify endpoint handles Trending category with 0 games gracefully."""
        self.trending_category.games.clear()
        url = reverse("trending_game")

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsNone(response.data["trending_game"])

    # -------------------------------------------------------------------------
    # 4. GAME DETAIL
    # -------------------------------------------------------------------------
    def test_game_detail_success(self):
        """Verify detail view returns game data for valid primary key."""
        url = reverse("game_details", kwargs={"pk": self.game1.pk})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], self.game1.pk)

    def test_game_detail_not_found(self):
        """Verify 404 status when querying non-existent game ID."""
        url = reverse("game_details", kwargs={"pk": 99999})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    # -------------------------------------------------------------------------
    # 5. CATEGORY GAMES
    # -------------------------------------------------------------------------
    def test_get_games_by_category_case_insensitive(self):
        """Verify category filtering works regardless of letter casing."""
        url = reverse("category-games", kwargs={"category_name": "action"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["category_name"], "Action")
        self.assertEqual(len(response.data["games"]), 1)

    def test_get_games_by_category_404(self):
        """Verify 404 error returned when non-existent category is queried."""
        url = reverse("category-games", kwargs={"category_name": "RPG"})
        response = self.client.get(url)

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["error"], "Category not found")