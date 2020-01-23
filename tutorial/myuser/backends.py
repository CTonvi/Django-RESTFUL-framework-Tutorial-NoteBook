from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from myuser.models import MyUser

from django.db.models import Q

class CustomeBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, captcha=None, **kwargs):
        try:
            user = MyUser.objects.get(Q(username=username) | Q(telephone=username))
            if user.check_password(password):
                return user
        except Exception as e:
            return None
        