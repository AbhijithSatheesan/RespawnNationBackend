from djoser.views import UserViewSet as DjoserUserViewSet
from django.db import transaction
from rest_framework.exceptions import ValidationError

class CustomUserViewSet(DjoserUserViewSet):
    def perform_create(self, serializer, *args, **kwargs):
        try:
            # The atomic block ensures that if the email fails, 
            # the database save is instantly rolled back.
            with transaction.atomic():
                super().perform_create(serializer, *args, **kwargs)
                
        except Exception as e:
            # You can print the real error to your console for debugging
            print(f"SMTP Email Failure: {e}")
            
            # Throw a clean 400 error formatted perfectly for your React frontend.
            # Djoser expects {"field_name": ["Error Message"]}
            raise ValidationError({
                "email": ["Email dispatch failed. Registration was cancelled so you can try again later."]
            })