from django.urls import path
from .views import *

urlpatterns = [
    path('hi/', hi, name= 'browse_games'),
    
   
]