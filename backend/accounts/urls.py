from django.urls import path
from .views import *

urlpatterns = [
    path('profile/me/', MyProfileView.as_view(), name = 'myprofile'),
    path('register/', register_user, name= 'register'),
    path('login/', login_user, name= 'login'),
    path('googlelogin/', GoogleLoginView.as_view(), name='googlelogin')
]