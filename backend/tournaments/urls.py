from django.urls import path
from .views import TournamentListView,TournamentDetailView

urlpatterns = [
    path('seetournaments/', TournamentListView.as_view(), name='tournament-list'),
    path('tournament/<int:id>/', TournamentDetailView.as_view(), name='tournament-detail'),
]