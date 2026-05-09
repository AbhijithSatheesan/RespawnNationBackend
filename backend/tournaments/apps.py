from django.apps import AppConfig

class TournamentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tournaments' # (Or whatever your app is named)

    # ADD THIS TO TURN ON YOUR SIGNALS
    def ready(self):
        import tournaments.signals