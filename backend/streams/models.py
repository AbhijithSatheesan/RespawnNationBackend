from django.db import models
from django.conf import settings
from games.models import Games
from tournaments.models import Tournament

# Create your models here.


class Stream(models.Model):
    STREAM_TYPES = [
        ('CLOUDFLARE', 'Cloudflare Live'),
        ('YOUTUBE', 'YouTube Live'),
        ('TWITCH', 'Twitch'),
    ]

    # Core Relationships
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='stream'
    )
    game = models.ForeignKey(
        Games,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='streams'
    )
    
    # The active tournament this stream is broadcasting
    active_tournament = models.ForeignKey(
        Tournament,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='live_streams'
    )

    # Stream details
    title = models.CharField(max_length=100, default='Untitled Stream')
    description = models.TextField(blank=True, null=True)

    # NEW: Platform routing
    stream_type = models.CharField(max_length=20, choices=STREAM_TYPES, default='CLOUDFLARE')
    external_url = models.URLField(max_length=500, blank=True, null=True, help_text="Used for Twitch or YouTube links")

    # Cloudflare Specifics
    cloudflare_id = models.CharField(max_length=100, blank=True, null=True, unique=True)
    stream_key = models.CharField(max_length=255, blank=True, null=True)
    playback_id = models.CharField(max_length=100, blank=True, null=True)

    is_live = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Stream"
    
    @property
    def hls_url(self):
        if self.stream_type == 'CLOUDFLARE' and self.playback_id:
            return f"https://videodelivery.net/{self.playback_id}/manifest/video.m3u8"
        return self.external_url