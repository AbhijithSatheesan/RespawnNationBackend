from django.contrib import admin
from django.contrib import messages # Lets us show success/error alerts
from django.utils.safestring import mark_safe
from django.db.models import F
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from .models import (
    Tournament, Participant, FootballStanding, 
    FootballMatch, BattleRoyaleMatch, BattleRoyaleResult
)
from .services import generate_football_group_stage # Import your new script!


# 1. THE TOURNAMENT
@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    # Notice we added 'generate_button' to the display list!
    list_display = ('title', 'game', 'status', 'max_players', 'generate_button')
    list_filter = ('status', 'game')
    search_fields = ('title',)

    # 1. Create a custom backend URL for the button to point to
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:tournament_id>/generate/', self.admin_site.admin_view(self.generate_brackets_view), name='generate_brackets'),
        ]
        return custom_urls + urls

    # 2. Inject the physical HTML button into the row
    def generate_button(self, obj):
        if obj.status == 'GENERATING':
            url = reverse('admin:generate_brackets', args=[obj.pk])
            # This creates a nice looking button in the admin panel
            return format_html(
                '<a class="button" style="background-color: #417690; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;" href="{}">Generate Brackets</a>', 
                url
            )
        # If the tournament is Live or Completed, just show a dash
        return format_html('<span style="color: gray;">-</span>')
    
    generate_button.short_description = 'Match Engine' # Column header name

    # 3. The engine logic that runs when the button is clicked
    def generate_brackets_view(self, request, tournament_id):
        tournament = self.get_object(request, tournament_id)
        
        if tournament.status == 'GENERATING':
            try:
                generate_football_group_stage(tournament)
                self.message_user(request, f"Successfully generated brackets for {tournament.title}!", messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f"Error generating brackets: {str(e)}", messages.ERROR)
        
        # Once done, immediately refresh the page!
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/tournaments/tournament/'))




# 2. THE PARTICIPANTS (The Pool)
@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'tournament', 'registered_at')
    list_filter = ('tournament',)
    search_fields = ('user__username', 'tournament__title')





# 3. FOOTBALL STATS & MATCHES
@admin.register(FootballStanding)
class FootballStandingAdmin(admin.ModelAdmin):
    list_display = ('participant', 'group_name', 'matches_played', 'goals_scored', 'goals_conceded', 'goal_difference', 'points')
    list_filter = ('participant__tournament', 'group_name')

    # --- NEW: THE UX BUTTON INJECTOR ---
    def changelist_view(self, request, extra_context=None):
        # Notice the URL parameter is different here!
        if 'participant__tournament__id__exact' not in request.GET:
            live_tournaments = Tournament.objects.filter(status='LIVE')
            
            if live_tournaments.exists():
                buttons_html = ""
                for t in live_tournaments:
                    # Link uses the 'participant__tournament__id__exact' parameter
                    buttons_html += f'<a href="?participant__tournament__id__exact={t.id}" style="background: #79aec8; color: white; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-weight: bold; margin-right: 10px; display: inline-block; margin-bottom: 5px;">{t.title}</a>'
                
                message = mark_safe(f"<div style='margin-bottom: 5px; font-size: 15px;'><b>Select a LIVE Tournament to view standings:</b><br><br>{buttons_html}</div>")
                messages.info(request, message)

        return super().changelist_view(request, extra_context)

    # --- EXISTING SHIELD LOGIC ---
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

    # --- NEW: THE UX BUTTON INJECTOR ---
    def changelist_view(self, request, extra_context=None):
        # If the user hasn't selected a tournament filter yet...
        if 'tournament__id__exact' not in request.GET:
            # Find all the tournaments that are currently live
            live_tournaments = Tournament.objects.filter(status='LIVE')
            
            if live_tournaments.exists():
                # Build physical HTML buttons for each one
                buttons_html = ""
                for t in live_tournaments:
                    # This creates a blue button that links exactly to this tournament's matches
                    buttons_html += f'<a href="?tournament__id__exact={t.id}" style="background: #79aec8; color: white; padding: 6px 12px; border-radius: 4px; text-decoration: none; font-weight: bold; margin-right: 10px; display: inline-block; margin-bottom: 5px;">{t.title}</a>'
                
                # Tell Django it is safe to render this HTML, and display it as a message!
                message = mark_safe(f"<div style='margin-bottom: 5px; font-size: 15px;'><b>Select a LIVE Tournament to manage matches:</b><br><br>{buttons_html}</div>")
                messages.info(request, message)
            else:
                messages.warning(request, "There are currently no LIVE tournaments.")

        return super().changelist_view(request, extra_context)

    # --- EXISTING SHIELD LOGIC ---
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        qs = qs.filter(tournament__status='LIVE')
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



# 4. BATTLE ROYALE (Using an Inline for the 100 players!)
class BattleRoyaleResultInline(admin.TabularInline):
    model = BattleRoyaleResult
    extra = 0 # Don't show empty rows by default




@admin.register(BattleRoyaleMatch)
class BattleRoyaleMatchAdmin(admin.ModelAdmin):
    list_display = ('tournament', 'match_number', 'is_completed')
    inlines = [BattleRoyaleResultInline] # This lets you add player results on the same page as the match!