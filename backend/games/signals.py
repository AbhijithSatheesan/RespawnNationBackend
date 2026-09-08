from django.db.models.signals import post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.cache import cache
from .models import Games, GameCategory

CACHE_KEY = "browse_games_feed"

# Clear cache whenever a Games record is created, updated, or deleted
@receiver([post_save, post_delete], sender=Games)
def clear_browse_games_cache_on_game_change(sender, instance, **kwargs):
    cache.delete(CACHE_KEY)

# Clear cache if GameCategory metadata changes
@receiver([post_save, post_delete], sender=GameCategory)
def clear_browse_games_cache_on_category_change(sender, instance, **kwargs):
    cache.delete(CACHE_KEY)

# Optional: Clear cache if games are added or removed from categories via ManyToMany
@receiver(m2m_changed, sender=GameCategory.games.through)
def clear_browse_games_cache_on_m2m_change(sender, instance, action, **kwargs):
    if action in ["post_add", "post_remove", "post_clear"]:
        cache.delete(CACHE_KEY)