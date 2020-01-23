import random
from django.http import HttpResponse
from myuser.Captcha import Captcha
from rest_framework_jwt.authentication import JSONWebTokenAuthentication
from myuser.models import MyUser
from rest_framework import viewsets
from rest_framework import mixins
from myuser.serializers import MyUserHyperSerializer, MyUserRegSerializer
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.reverse import reverse
from rest_framework.permissions import IsAuthenticated
from rest_framework_jwt.serializers import jwt_encode_handler, jwt_payload_handler

# Create your views here.

# 验证码字符
ALL_CHARS = '0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

# API初始入口
@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'users': reverse('myusers', request=request, format=format),
        'captcha': reverse('get_captcha', request=request, format=format),
        'login': reverse('login', request=request, format=format),
        'token_refresh': reverse('token_refresh', request=request, format=format),
    })

def get_captcha(request):
    """获得验证码"""
    length = int(request.GET.get('len', '4'))
    selected_chars = random.choices(ALL_CHARS, k=length)
    captcha_text = ''.join(selected_chars)
    image = Captcha.instance().generate(captcha_text)
    request.session['captcha'] = captcha_text

    return HttpResponse(image, content_type='image/png')

class MyUserViewSet(viewsets.ModelViewSet):

    queryset = MyUser.objects.all()
    serializer_class = MyUserHyperSerializer
    permission_classes = []
    authentication_classes = [JSONWebTokenAuthentication,]
    permission_classes_map = {
        'list': [IsAuthenticated, ]
    }

    def initial(self, request, *args, **kwargs):
        """重新定义此方法，添加灵活配置权限映射"""
        if request.method.lower() in self.http_method_names:
            handler = getattr(self, request.method.lower(), self.http_method_not_allowed)
        else:
            handler = self.http_method_not_allowed

        if hasattr(handler, '__name__'):
            handler_name = handler.__name__
        elif hasattr(handler, '__func__'):
            handler_name = handler.__func__.__name__
        else:
            handler_name = None

        if handler_name and handler_name in self.permission_classes_map:
            if isinstance(self.permission_classes_map.get(handler_name), (tuple, list)):
                self.permission_classes = self.permission_classes_map.get(handler_name)
        return super(MyUserViewSet, self).initial(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        
        # 验证码比对
        if not request.session.get('captcha', '') or \
            request.session.get('captcha').lower() != request.data.get('captcha', '').lower():
            return Response({'detail': 'captcha does not match'}, status=status.HTTP_400_BAD_REQUEST)

        serializer = MyUserRegSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = self.perform_create(serializer)

        # 此处生成token
        res_dict = serializer.data
        payload = jwt_payload_handler(user)
        res_dict['token'] = jwt_encode_handler(payload)

        headers = self.get_success_headers(serializer.data)
        return Response(res_dict, status=status.HTTP_201_CREATED, headers=headers)
    
    def perform_create(self, serializer):
        return serializer.save()

class JSONWebTokenAPIViewWithCaptcha(JSONWebTokenAuthentication):
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        if serializer.is_valid():
            user = serializer.object.get('user') or request.user
            token = serializer.object.get('token')
            response_data = jwt_response_payload_handler(token, user, request)
            response = Response(response_data)
            if api_settings.JWT_AUTH_COOKIE:
                expiration = (datetime.utcnow() +
                              api_settings.JWT_EXPIRATION_DELTA)
                response.set_cookie(api_settings.JWT_AUTH_COOKIE,
                                    token,
                                    expires=expiration,
                                    httponly=True)
            return response

class ObtainJSONWebTokenWithCaptcha(JSONWebTokenAPIViewWithCaptcha):
    pass    