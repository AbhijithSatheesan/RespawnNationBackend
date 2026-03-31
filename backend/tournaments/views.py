from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from .models import Tournament
from .serializers import TournamentSerializer, TournamentDetailSerializer

# 1. Create a custom Pagination class for your Tournaments
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 2 # Fetch 10 at a time
    page_size_query_param = 'page_size'
    max_page_size = 50

class TournamentListView(generics.ListAPIView):
    serializer_class = TournamentSerializer
    pagination_class = StandardResultsSetPagination # 2. Tell the view to use it

    def get_queryset(self):
        queryset = Tournament.objects.all()
        requested_status = self.request.query_params.get('status', None)

        if requested_status:
            queryset = queryset.filter(status=requested_status)

        # 3. Just order them, the pagination class will handle the slicing automatically!
        return queryset.order_by('registration_deadline')
    




class TournamentDetailView(generics.RetrieveAPIView):
    queryset = Tournament.objects.all()
    serializer_class = TournamentDetailSerializer
    lookup_field = 'id' # This tells Django to look up by the URL ID