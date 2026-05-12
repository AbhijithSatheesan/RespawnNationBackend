from django.urls import path
from .views import *
from .wallet import RequestWithdrawalView

urlpatterns = [
    path('profile/me/', MyProfileView.as_view(), name = 'myprofile'),
    path('register/', register_user, name= 'register'),
    path('login/', login_user, name= 'login'),
    path('googlelogin/', GoogleLoginView.as_view(), name='googlelogin'),

    # Wallet
    path('wallet/withdraw/', RequestWithdrawalView.as_view(), name='wallet-withdraw')

]