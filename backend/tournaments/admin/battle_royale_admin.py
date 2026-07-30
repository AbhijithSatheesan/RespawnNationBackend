from django.contrib import admin
from ..models import BattleRoyaleMatch, BattleRoyaleResult

class BattleRoyaleResultInline(admin.TabularInline):
    model = BattleRoyaleResult
    extra = 3     
    max_num = 3   
    fields = ('rank', 'participant', 'kills')
    ordering = ('rank',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == 'participant':
            match_id = request.resolver_match.kwargs.get('object_id')
            if match_id:
                match = BattleRoyaleMatch.objects.get(pk=match_id)
                kwargs["queryset"] = match.tournament.participants.all()
            else:
                kwargs["queryset"] = db_field.related_model.objects.none()

        return super().formfield_for_foreignkey(db_field, request, **kwargs)

@admin.register(BattleRoyaleMatch)
class BattleRoyaleMatchAdmin(admin.ModelAdmin):
    list_display = ('tournament', "match_number", 'is_completed')
    list_filter = ('tournament', 'is_completed')
    search_fields = ("tournament__title",)
    inlines = [BattleRoyaleResultInline]