from django.urls import path
from .views import *


urlpatterns = [
    path("my-stream/", MyStreamView.as_view()),
    path('create-stream/', CreateStreamVIew.as_view()),
    path('regenerate-key/', RegenerateStreamKeyView.as_view(), name='regenerate-key'),
    path("live/", LiveStreamsListView.as_view()),
    path("<int:pk>/", StreamDetailVeiw.as_view()),
    path('my-stream/update/', UpdateStreamView.as_view(), name='update-stream'),
    
]
