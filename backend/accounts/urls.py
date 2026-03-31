from django.urls import path
from .views import *

urlpatterns = [
    path('register/', register_user, name= 'register'),
    path('login/', login_user, name= 'login'),
    path('googlelogin/', GoogleLoginView.as_view(), name='googlelogin')
]