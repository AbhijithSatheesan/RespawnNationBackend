from django.contrib import admin
from django.contrib import messages
from django.utils.safestring import mark_safe
from ..models import Tournament, Participant, FootballStanding, FootballMatch

@admin.register(FootballStanding)
class FootballStandingAdmin(admin.ModelAdmin):
    list_display = ('participant', 'group_name', 'matches_played', 'goals_scored', 'goals_conceded', 'goal_difference', 'points')
    list_filter = ('participant__tournament', 'group_name')

    def changelist_view(self, request, extra_context=None):
        if 'participant__tournament__id__exact' not in request.GET:
            live_tournaments = Tournament.objects.filter(status='LIVE')
            if live_tournaments.exists():
                buttons_html = ""
                for t in live_tournaments:
                    buttons_html += f'<a href="?participant__tournament__id__exact={t.id}" style="background: #79aec8; color: white; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-weight: bold; margin-right: 10px; display: inline-block; margin-bottom: 5px;">{t.title}</a>'
                message = mark_safe(f"<div style='margin-bottom: 5px; font-size: 15px;'><b>Select a LIVE Tournament to view standings:</b><br><br>{buttons_html}</div>")
                messages.info(request, message)

        return super().changelist_view(request, extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        from django.db.models import F
        qs = qs.annotate(goal_difference=F('goals_scored') - F('goals_conceded'))

        if request.resolver_match and request.resolver_match.url_name.endswith('_changelist'):
            if 'participant__tournament__id__exact' not in request.GET:
                return qs.none()

        return qs.order_by('-points', '-goal_difference')
    
    @admin.display(ordering='goal_difference', description='GD')
    def goal_difference(self, obj):
        return obj.goal_difference

@admin.register(FootballMatch)
class FootballMatchAdmin(admin.ModelAdmin):
    list_display = ('tournament', "match_number", 'round_name', 'player_1', 'player_2', 'is_completed')
    list_filter = ('tournament', 'stage', 'is_completed')
    search_fields = ('player_1__user__username', 'player_2__user__username')
    ordering = ('tournament', 'match_number')
    list_select_related = ('tournament', 'player_1__user', 'player_2__user')
    list_per_page = 50 

    def changelist_view(self, request, extra_context=None):
        if 'tournament__id__exact' not in request.GET:
            live_tournaments = Tournament.objects.filter(status='LIVE')
            if live_tournaments.exists():
                buttons_html = ""
                for t in live_tournaments:
                    buttons_html += f'<a href="?tournament__id__exact={t.id}" style="background: #79aec8; color: white; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-weight: bold; margin-right: 10px; display: inline-block; margin-bottom: 5px;">{t.title}</a>'
                message = mark_safe(f"<div style='margin-bottom: 5px; font-size: 15px;'><b>Select a LIVE Tournament to manage matches:</b><br><br>{buttons_html}</div>")
                messages.info(request, message)
            else:
                messages.warning(request, "There are currently no LIVE tournaments.")

        return super().changelist_view(request, extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.resolver_match and request.resolver_match.url_name.endswith('_changelist'):
            if 'tournament__id__exact' not in request.GET:
                return qs.none()
        return qs

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj and obj.player_1 and obj.player_2:
            form.base_fields['winner'].queryset = Participant.objects.filter(
                id__in=[obj.player_1.id, obj.player_2.id]
            )
        return form