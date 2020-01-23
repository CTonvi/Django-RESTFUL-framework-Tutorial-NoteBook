from django.urls import path, include
from myuser import views
from rest_framework.urlpatterns import format_suffix_patterns
from rest_framework import renderers
from rest_framework_jwt.views import obtain_jwt_token, refresh_jwt_token


users = views.MyUserViewSet.as_view({
    'get': 'list',
    'post': 'create',
})

user_detail = views.MyUserViewSet.as_view({
    'get': 'retrieve',
})

urlpatterns = format_suffix_patterns([
    path('', users, name='myusers'),
    path('<int:pk>/', user_detail, name='myuser-detail'),
    path('api-auth/',include('rest_framework.urls')),
    path('login/', obtain_jwt_token, name='login'),
    path('refresh/', refresh_jwt_token, name='token_refresh'),
    path('captcha/', views.get_captcha, name='get_captcha'),
])

