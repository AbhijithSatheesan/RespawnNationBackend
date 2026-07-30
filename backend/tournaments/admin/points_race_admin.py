from django.contrib import admin
from django.utils.html import format_html
# Replace with your actual Points Race model names if different
from ..models import PointsRaceMatch, PointsRaceStanding 


@admin.register(PointsRaceMatch)
class PointsRaceMatchAdmin(admin.ModelAdmin):
    list_display = (
        'tournament', 
        'match_number', 
        'player_1', 
        'player_2', 
        'p1_score', 
        'p2_score', 
        'status_badge', 
        'winner'
    )
    list_filter = ('status', 'tournament')
    search_fields = (
        'player_1__user__username', 
        'player_2__user__username', 
        'tournament__title'
    )
    ordering = ('tournament', 'match_number')

    def status_badge(self, obj):
        colors = {
            'PENDING': '#6c757d',
            'SCHEDULED': '#17a2b8',
            'LIVE': '#dc3545',
            'AWAITING_REVIEW': '#ffc107',
            'COMPLETED': '#28a745',
            'DISPUTED': '#e83e8c',
        }
        color = colors.get(obj.status, '#000000')
        return format_html(
            '<span style="background-color: {}; color: white; padding: 3px 8px; border-radius: 3px; font-weight: bold; font-size: 11px;">{}</span>',
            color, obj.get_status_display()
        )
    status_badge.short_description = 'Status'


@admin.register(PointsRaceStanding)
class PointsRaceStandingAdmin(admin.ModelAdmin):
    list_display = ('participant', 'total_points', 'matches_played', 'target_reached')
    search_fields = ('participant__user__username', 'participant__tournament__title')
    ordering = ('-total_points',)

    def target_reached(self, obj):
        if obj.total_points >= 50:  # Example target threshold
            return format_html('<span style="color: green; font-weight: bold;">✔ Qualified</span>')
        return format_html('<span style="color: gray;">In Progress</span>')
    
    target_reached.short_description = 'Target Status'