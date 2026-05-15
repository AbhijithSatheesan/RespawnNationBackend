from django.contrib import admin
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.db import transaction
from decimal import Decimal
from .models import (
    Tournament, Participant, FootballStanding, 
    FootballMatch, BattleRoyaleMatch, BattleRoyaleResult, TournamentType
)

from .engines.factory import get_tournament_engine

from accounts.models import UserProfile, WalletTransaction

admin.site.register(TournamentType)

# 1. THE TOURNAMENT
@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    # Added 'prizes_distributed' so you can see it easily in the list view
    list_display = ('title', 'game', 'status', 'max_players', 'display_prize_pool', 'generate_button', 'prizes_distributed')
    list_filter = ('status', 'game', 'tournament_type')
    search_fields = ('title',)

    # Register the payout action
    actions = ['distribute_prize_money']


    def display_prize_pool(self, obj):
        # Grabs the dynamic property from your model and formats it nicely
        return format_html('<span style="font-weight: bold; color: #28a745;">₹{}</span>', obj.current_prize_pool)
    
    # This sets the column header name in the admin panel
    display_prize_pool.short_description = 'Prize Pool'

    # =========================================================================
    # THE PAYOUT ACTION (WALLET INTEGRATION)
    # =========================================================================
    @admin.action(description='💰 Distribute Prizes (70/30) & Close Tournament')
    def distribute_prize_money(self, request, queryset):
        success_count = 0

        for tournament in queryset:
            # Safety Check 1: Already paid?
            if tournament.prizes_distributed:
                self.message_user(request, f"Skipped '{tournament.title}': Prizes already distributed.", level=messages.WARNING)
                continue
            
            # Safety Check 2: Is there a winner?
            if not tournament.winner:
                self.message_user(request, f"Skipped '{tournament.title}': You must select a Winner first.", level=messages.ERROR)
                continue

            total_pool = tournament.current_prize_pool
            
            # CALCULATE SPLITS: 70% Winner, 30% Runner-Up
            winner_cut = total_pool * Decimal('0.70')
            runner_up_cut = total_pool * Decimal('0.30')

            with transaction.atomic():
                # --- PAY THE WINNER ---
                # Safely ensure the profile exists before trying to lock it
                UserProfile.objects.get_or_create(user=tournament.winner.user)
                
                # Now lock it and pay them
                winner_profile = UserProfile.objects.select_for_update().get(user=tournament.winner.user)
                winner_profile.wallet_balance += winner_cut
                winner_profile.total_earnings += winner_cut
                winner_profile.save()

                WalletTransaction.objects.create(
                    user=tournament.winner.user,
                    amount=winner_cut,
                    transaction_type='PRIZE',
                    description=f"1st Place (70%) - {tournament.title}",
                    tournament=tournament
                )

                # --- PAY THE RUNNER UP (If they exist) ---
                if tournament.runner_up:
                    # Safely ensure the profile exists before trying to lock it
                    UserProfile.objects.get_or_create(user=tournament.runner_up.user)
                    
                    # Now lock it and pay them
                    runner_up_profile = UserProfile.objects.select_for_update().get(user=tournament.runner_up.user)
                    runner_up_profile.wallet_balance += runner_up_cut
                    runner_up_profile.total_earnings += runner_up_cut
                    runner_up_profile.save()

                    WalletTransaction.objects.create(
                        user=tournament.runner_up.user,
                        amount=runner_up_cut,
                        transaction_type='PRIZE',
                        description=f"2nd Place (30%) - {tournament.title}",
                        tournament=tournament
                    )

                # --- LOCK THE TOURNAMENT ---
                tournament.status = 'COMPLETED'
                tournament.prizes_distributed = True
                tournament.save()
                
                success_count += 1

        if success_count > 0:
            self.message_user(request, f"Successfully distributed prizes for {success_count} tournaments!", level=messages.SUCCESS)


    # =========================================================================
    # SMART DROPDOWN FILTERING
    # =========================================================================
    def get_form(self, request, obj=None, **kwargs):
        # 1. Get the default form Django generated
        form = super().get_form(request, obj, **kwargs)
        
        # 2. Check if we are editing an existing tournament (obj exists)
        if obj:
            # Filter the dropdowns to ONLY show participants of this specific tournament
            if 'winner' in form.base_fields:
                form.base_fields['winner'].queryset = Participant.objects.filter(tournament=obj)
            if 'runner_up' in form.base_fields:
                form.base_fields['runner_up'].queryset = Participant.objects.filter(tournament=obj)
        else:
            # 3. If creating a brand new tournament, hide all participants 
            # (Because you can't have a winner for a tournament that hasn't been saved yet)
            if 'winner' in form.base_fields:
                form.base_fields['winner'].queryset = Participant.objects.none()
            if 'runner_up' in form.base_fields:
                form.base_fields['runner_up'].queryset = Participant.objects.none()
            
        return form

    # =========================================================================
    # ENGINE & MATCH GENERATION METHODS
    # =========================================================================
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:tournament_id>/generate/', self.admin_site.admin_view(self.generate_brackets_view), name='generate_brackets'),
            path('<int:tournament_id>/generate_knockouts/', self.admin_site.admin_view(self.generate_knockouts_view), name='generate_knockouts'),
        ]
        return custom_urls + urls

    def generate_button(self, obj):
        # Safely grab the engine code
        engine_code = obj.tournament_type.engine_code if obj.tournament_type else None

        if obj.status == 'GENERATING':
            url = reverse('admin:generate_brackets', args=[obj.pk])
            
            # Change text based on the format
            if engine_code == 'world_cup':
                button_text = 'Generate Groups'
            elif engine_code == 'battle_royale':
                button_text = 'Generate Lobbies'
            else:
                button_text = 'Generate Matches'
                
            return format_html(
                '<a class="button" style="background-color: #417690; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;" href="{}">{}</a>', 
                url, button_text
            )
        
        elif obj.status == 'LIVE':
            # World Cup logic requires Knockout checking
            if engine_code == 'world_cup':
                if obj.football_matches.filter(stage='KNOCKOUT').exists():
                    return format_html('<span style="color: green; font-weight: bold;">Knockouts Active</span>')
                else:
                    url = reverse('admin:generate_knockouts', args=[obj.pk])
                    return format_html(
                        '<a class="button" style="background-color: #ba2121; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;" href="{}" ' \
                        'onclick="return confirm(\'Make sure all group matches are completed. Generate knockouts now?\');">Start Knockouts</a>', 
                        url
                    )
            
            # Battle Royale has no knockouts, just show Live status
            elif engine_code == 'battle_royale':
                return format_html('<span style="color: green; font-weight: bold;">Lobbies Active</span>')
            
            else:
                return format_html('<span style="color: green; font-weight: bold;">Live</span>')
        
        elif obj.status == 'COMPLETED':
            return format_html('<span style="color: goldenrod; font-weight: bold;">🏆 Finished</span>')
            
        return format_html('<span style="color: gray;">-</span>')
    
    generate_button.short_description = 'Match Engine'

    def generate_brackets_view(self, request, tournament_id):
        tournament = self.get_object(request, tournament_id)
        
        if tournament.status == 'GENERATING':
            try:
                # Use the factory to run the correct format
                engine = get_tournament_engine(tournament)
                engine.generate_initial_matches()
                
                self.message_user(request, f"Successfully generated matches for {tournament.title}!", messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f"Error generating matches: {str(e)}", messages.ERROR)
        
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/tournaments/tournament/'))

    def generate_knockouts_view(self, request, tournament_id):
        tournament = self.get_object(request, tournament_id)
        
        if tournament.status == 'LIVE':
            try:
                # Use the factory to run the correct knockout logic
                engine = get_tournament_engine(tournament)
                engine.generate_knockouts()
                
                self.message_user(request, f"Knockout brackets generated for {tournament.title}!", messages.SUCCESS)
            except Exception as e:
                self.message_user(request, f"Error: {str(e)}", messages.ERROR)
                
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





#   <------------------------ BATTLE ROYALE ---------------------------->

# score card
class BattleRoyaleResultInline(admin.TabularInline):
    model = BattleRoyaleResult

    extra = 3     # show only three rows by default because we are only considering only top 3
    max_num = 3   # makes sure only three is added

    fields = ('rank', 'participant', 'kills')
    ordering = ('rank',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'participant':
            # grab the match id from url
            match_id = request.resolver_match.kwargs.get('object_id')

            if match_id:
                # if the match id exists then find the tournament it is connected to
                match = BattleRoyaleMatch.objects.get(pk = match_id)

                # now filter the dropdown with only the participants available in that tournament
                kwargs["queryset"] = match.tournament.participants.all()

            else:
                # if no player was added
                kwargs["queryset"] = db_field.related_model.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)


# the match dashboard
@admin.register(BattleRoyaleMatch)
class BattleRoyaleMatchAdmin(admin.ModelAdmin):
    list_display = ('tournament', "match_number", 'is_completed')
    list_filter = ('tournament', 'is_completed')
    search_fields = ("tournament__title",)

    # injest top 3 scorecard into match page
    inlines = [BattleRoyaleResultInline]
    









