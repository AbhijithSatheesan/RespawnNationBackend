from django.urls import path
from .views import TournamentListView,TournamentDetailView, GenerateOrderView, RegisterTournamentView

urlpatterns = [
    path('seetournaments/', TournamentListView.as_view(), name='tournament-list'),
    path('tournament/<int:id>/', TournamentDetailView.as_view(), name='tournament-detail'),
    path('<int:pk>/generate_order/', GenerateOrderView.as_view(), name= 'generate-order'),
    path('<int:pk>/register/', RegisterTournamentView.as_view(), name='register-tournament')
]