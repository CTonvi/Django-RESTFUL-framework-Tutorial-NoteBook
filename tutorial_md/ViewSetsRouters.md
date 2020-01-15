REST framework中的`ViewSet`可以帮开发者省去构建`URLConf`的功夫，专注于数据建模和API关联的开发；`ViewSet`和`view`大致相同，不同的是`ViewSet`提供`read`、`update`等，而不是`get`或`put`；

当实例化一组视图时，`ViewSet`就会传入一组方法映射，典型的例子是结合能轻松解决复杂URLConf的`Router`来使用


## 重构我们的视图
首先我们使用单个`UserViewSet`来重构代替`UserList`和`UserDetail`
```python
from rest_framework import viewsets

class UserViewSet(viewsets.ReadOnlyModelViewSet):
    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
```
其中的`ReadOnlyModelViewsSet`自动提供默认的只读操作；我们仍要设置`queryset`和`serializer_class`的值，这和我们使用常规视图差不多，不过我们省去了设置`queryset`和`serializer_class`的重复步骤

然后就是重写`SnippetList`,`SnippetDetial`和`SnippetHighlight`视图类
```python
from rest_framework.decorators import action
from rest_framework.response import Response

class SnippetViewSet(viewsets.ModelViewSet):
    """
    This viewset automatically provides `list`, `create`, `retrieve`,
    `update` and `destroy` actions.

    Additionally we also provide an extra `highlight` action.
    """
    queryset = Snippet.objects.all()
    serializer_class = SnippetSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly,
                          IsOwnerOrReadOnly]

    @action(detail=True, renderer_classes=[renderers.StaticHTMLRenderer])
    def highlight(self, request, *args, **kwargs):
        snippet = self.get_object()
        return Response(snippet.highlighted)

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)
```
使用`ModelViewSet`获取完整的读写方法；

装饰器`@action`可以创建一个自定义方法，命名为`highlight`;如果模块自带的方法不能满足你的需求，自定义是个解决方法；

自定义的方法默认响应`GET`请求，你也可以通过添加`methods=['POST']`来响应`POST`请求；

自定义方法的URLs默认依赖于方法名，你也可以通过导入`url_path`来作为装饰器的关键字参数来改变(??)


## 配置URLConf
只有配置了对应URLConf，请求才会跳转到对应的视图函数；
下面看看如果对`ViewSet`类型的视图配置URLConf
```python
# snippets/urls.py

from snippets.views import SnippetViewSet, UserViewSet, api_root
from rest_framework import renderers

snippet_list = SnippetViewSet.as_view({
    'get': 'list',
    'post': 'create'
})
snippet_detail = SnippetViewSet.as_view({
    'get': 'retrieve',
    'put': 'update',
    'patch': 'partial_update',
    'delete': 'destroy'
})
snippet_highlight = SnippetViewSet.as_view({
    'get': 'highlight'
}, renderer_classes=[renderers.StaticHTMLRenderer])
user_list = UserViewSet.as_view({
    'get': 'list'
})
user_detail = UserViewSet.as_view({
    'get': 'retrieve'
})
```
我们重一个`ViewSet`类中构建除了多个视图，根据需求传入`方法映射字典`，就能构建出合适视图，非常简便好用，最后是注册到URLConf中去
```python
urlpatterns = format_suffix_patterns([
    path('', api_root),
    path('snippets/', snippet_list, name='snippet-list'),
    path('snippets/<int:pk>/', snippet_detail, name='snippet-detail'),
    path('snippets/<int:pk>/highlight/', snippet_highlight, name='snippet-highlight'),
    path('users/', user_list, name='user-list'),
    path('users/<int:pk>/', user_detail, name='user-detail')
])
```


## 使用Routers
使用`ViewSet`取代`View`简化了很多代码量，同样的我们也可以选择不用自己去设计URLConf，使用`Router`可以自动完成URLConf，我们要做的是把对应的视图集注册进去
```python
# snippets/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from snippets import views

# Create a router and register our viewsets with it.
router = DefaultRouter()
router.register(r'snippets', views.SnippetViewSet)
router.register(r'users', views.UserViewSet)

# The API URLs are now determined automatically by the router.
urlpatterns = [
    path('', include(router.urls)),
]
```
用注册的方式配置URLConf和前面手写urlpattern差不多，我们需要提供两个参数，第一个是`URL的前缀`，第二个是对应的`ViewSet`；另外`DefaultRouter`会自动创建`根访问点`，所以我们之前在`views.py`中写的`api_root`函数视图可以删去了；

## ViewSet和View的选择
使用`ViewSet`能高度抽象化API，确保URL和API的完全对应，能最小化代码量，能让开发人员专注于API之间的关联；

但还是要根据业务需求而定，毕竟使用`View`的定制能力比`ViewSet`强