from django.urls import path
from .views import *
from .wallet import RequestWithdrawalView, GenerateDepositOrderView, VerifyDepositView

urlpatterns = [
    path('profile/me/', MyProfileView.as_view(), name = 'myprofile'),

    # path('register/', register_user, name= 'register'),
    # path('login/', login_user, name= 'login'),

    path('googlelogin/', GoogleLoginView.as_view(), name='googlelogin'),

    # Wallet
    path('wallet/withdraw/', RequestWithdrawalView.as_view(), name='wallet-withdraw'),
    path('wallet/deposit/generate/', GenerateDepositOrderView.as_view(), name='generate-deposit-order'),
    path('wallet/deposit/verify/', VerifyDepositView.as_view(), name='verify-deposit'),

]