from django.contrib import admin
from django.contrib import messages
from django.utils.safestring import mark_safe
from django.utils.html import format_html
from django.urls import path, reverse
from django.http import HttpResponseRedirect
from django.db import transaction
from decimal import Decimal

# Models and factory imports
from ..models import Tournament, Participant, TournamentType
from ..engines.factory import get_tournament_engine
from accounts.models import UserProfile, WalletTransaction


admin.site.register(TournamentType)


@admin.register(Tournament)
class TournamentAdmin(admin.ModelAdmin):
    list_display = (
        'title', 
        'game', 
        'status', 
        'max_players', 
        'display_prize_pool', 
        'generate_button', 
        'prizes_distributed'
    )
    list_filter = ('status', 'game', 'tournament_type')
    search_fields = ('title',)
    actions = ['distribute_prize_money']

    def display_prize_pool(self, obj):
        return format_html(
            '<span style="font-weight: bold; color: #28a745;">₹{}</span>', 
            obj.current_prize_pool
        )
    
    display_prize_pool.short_description = 'Prize Pool'

    @admin.action(description='💰 Distribute Prizes (70/30) & Close Tournament')
    def distribute_prize_money(self, request, queryset):
        success_count = 0
        for tournament in queryset:
            if tournament.prizes_distributed:
                self.message_user(
                    request, 
                    f"Skipped '{tournament.title}': Prizes already distributed.", 
                    level=messages.WARNING
                )
                continue
            
            if not tournament.winner:
                self.message_user(
                    request, 
                    f"Skipped '{tournament.title}': You must select a Winner first.", 
                    level=messages.ERROR
                )
                continue

            total_pool = tournament.current_prize_pool
            winner_cut = total_pool * Decimal('0.70')
            runner_up_cut = total_pool * Decimal('0.30')

            with transaction.atomic():
                # 1. Update Winner Profile & Wallet
                UserProfile.objects.get_or_create(user=tournament.winner.user)
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

                # 2. Update Runner Up Profile & Wallet (if exists)
                if tournament.runner_up:
                    UserProfile.objects.get_or_create(user=tournament.runner_up.user)
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

                # 3. Finalize Tournament Status
                tournament.status = 'COMPLETED'
                tournament.prizes_distributed = True
                tournament.save()
                success_count += 1

        if success_count > 0:
            self.message_user(
                request, 
                f"Successfully distributed prizes for {success_count} tournament(s)!", 
                level=messages.SUCCESS
            )

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:
            if 'winner' in form.base_fields:
                form.base_fields['winner'].queryset = Participant.objects.filter(tournament=obj)
            if 'runner_up' in form.base_fields:
                form.base_fields['runner_up'].queryset = Participant.objects.filter(tournament=obj)
        else:
            if 'winner' in form.base_fields:
                form.base_fields['winner'].queryset = Participant.objects.none()
            if 'runner_up' in form.base_fields:
                form.base_fields['runner_up'].queryset = Participant.objects.none()
        return form

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:tournament_id>/generate/', 
                self.admin_site.admin_view(self.generate_brackets_view), 
                name='generate_brackets'
            ),
            path(
                '<int:tournament_id>/generate_knockouts/', 
                self.admin_site.admin_view(self.generate_knockouts_view), 
                name='generate_knockouts'
            ),
        ]
        return custom_urls + urls

    def generate_button(self, obj):
        engine_code = obj.tournament_type.engine_code if obj.tournament_type else None

        # --- STATE 1: GENERATING BRACKETS / FIXTURES ---
        if obj.status == 'GENERATING':
            url = reverse('admin:generate_brackets', args=[obj.pk])
            
            if engine_code == 'world_cup':
                button_text = 'Generate Groups'
            elif engine_code == 'battle_royale':
                button_text = 'Generate Lobbies'
            elif engine_code == 'points_race':
                button_text = 'Generate Arena Fixtures'
            else:
                button_text = 'Generate Matches'
                
            return format_html(
                '<a class="button" style="background-color: #417690; color: white; padding: 5px 10px; border-radius: 4px; font-weight: bold;" href="{}">{}</a>', 
                url, button_text
            )

        # --- STATE 2: LIVE TOURNAMENT ---
        elif obj.status == 'LIVE':
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
            elif engine_code == 'battle_royale':
                return format_html('<span style="color: green; font-weight: bold;">Lobbies Active</span>')
            elif engine_code == 'points_race':
                return format_html('<span style="color: green; font-weight: bold;">Arena Live</span>')
            else:
                return format_html('<span style="color: green; font-weight: bold;">Live</span>')

        # --- STATE 3: FINISHED ---
        elif obj.status == 'COMPLETED':
            return format_html('<span style="color: goldenrod; font-weight: bold;">🏆 Finished</span>')
        
        return format_html('<span style="color: gray;">-</span>')
    
    generate_button.short_description = 'Match Engine'

    def generate_brackets_view(self, request, tournament_id):
        tournament = self.get_object(request, tournament_id)
        if tournament.status == 'GENERATING':
            try:
                engine = get_tournament_engine(tournament)
                engine.generate_initial_matches()
                self.message_user(
                    request, 
                    f"Successfully generated initial matches/fixtures for {tournament.title}!", 
                    messages.SUCCESS
                )
            except Exception as e:
                self.message_user(request, f"Error generating matches: {str(e)}", messages.ERROR)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/tournaments/tournament/'))

    def generate_knockouts_view(self, request, tournament_id):
        tournament = self.get_object(request, tournament_id)
        if tournament.status == 'LIVE':
            try:
                engine = get_tournament_engine(tournament)
                engine.generate_knockouts()
                self.message_user(
                    request, 
                    f"Knockout brackets generated for {tournament.title}!", 
                    messages.SUCCESS
                )
            except Exception as e:
                self.message_user(request, f"Error generating knockouts: {str(e)}", messages.ERROR)
        return HttpResponseRedirect(request.META.get('HTTP_REFERER', '/admin/tournaments/tournament/'))


@admin.register(Participant)
class ParticipantAdmin(admin.ModelAdmin):
    list_display = ('user', 'tournament', 'registered_at')
    list_filter = ('tournament',)
    search_fields = ('user__username', 'tournament__title')