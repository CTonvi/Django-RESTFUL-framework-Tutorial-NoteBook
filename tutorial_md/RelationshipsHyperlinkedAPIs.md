目前API之间通过使用外键的来进行关联的；接下来我们需要提高API的内聚和可发现性(?)，所以我们将使用`hyperlinking`来进行关联
<br>

## 为root接口创建访问点(endpoint)
现在`snippets`和`users`已经有专门的访问点，但我们还没有为总的接口设置一个访问点；我们将使用一个函数视图结合装饰器`@api_view`来创建一个
```python
## snippets/veiws.py
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse


@api_view(['GET'])
def api_root(request, format=None):
    return Response({
        'users': reverse('user-list', request=request, format=format),
        'snippets': reverse('snippet-list', request=request, format=format)
    })
```
有两个需要注意的点是<br>
1. 使用REST framework的 `reverse`函数可以返回完整的 URLs
2. URL_patterns的名字需要在 snippets/urls.py添加。
<br>

## 为代码高亮添加访问点
与其他API访问点不同，代码高亮不返回JSON，而是返回渲染的HTML；REST framework提供了两种类型的HTML渲染方式：<br>
1. 使用模板进行渲染
2. 使用预渲染的HMTL<br>
接下来我们将使用第二种<br>

另外我们还需要考虑的是代码高亮并不是一个完整的实例对象，它只是实例对象中的一个属性，所以并没有现成的 generic view 供我们使用，所以我们需要自己去写`.get()`方法
```python
from rest_framework import renderers
from rest_framework.response import Response

class SnippetHighlight(generics.GenericAPIView):
    queryset = Snippet.objects.all()
    renderer_classes = [renderers.StaticHTMLRenderer]   # 预渲染

    def get(self, request, *args, **kwargs):
        snippet = self.get_object()
        return Response(snippet.highlighted)
```
添加URLConf
```python
## snippets/urls.py
path('', views.api_root),
path('snippets/<int:pk>/highlight/', views.SnippetHighLight.as_view()),
```
<br>

## Hyperlinking
实体关联的形式是Web API设计的重要一环，下面罗列下可能会成为选择的形式
1. 使用主键
2. 实体间使用超链接关联
3. 使用关联实体中带`unique`性质的字段
4. 使用默认的字符串表述
5. ?
6. 自定义
<br>

下面我们将使用超链接的形式(`Hyperlinking`)

首先我们需要把序列化器由 `ModelSerializer` 更改为 `HyperlinkedModelSerializer`， 后者和前者的区别在于：
1. 后者中默认不包含`id`字段
2. 后者包含`url`字段，使用`HyperlinkedIdentityField`字段类来创建
3. 关联方式使用`HyperlinkedRelatedField`而不是`PrimaryKeyRelatedField`

重写的方式非常简单
```python
class SnippetSerializer(serializers.HyperlinkedModelSerializer):
    owner = serializers.ReadOnlyField(source='owner.username')
    highlight = serializers.HyperlinkedIdentityField(view_name='snippet-highlight', format='html')

    class Meta:
        model = Snippet
        fields = ['url', 'id', 'highlight', 'owner',
                  'title', 'code', 'linenos', 'language', 'style']


class UserSerializer(serializers.HyperlinkedModelSerializer):
    snippets = serializers.HyperlinkedRelatedField(many=True, view_name='snippet-detail', read_only=True)

    class Meta:
        model = User
        fields = ['url', 'id', 'username', 'snippets']
```
我们还为`Snippet`序列化器添加了`highlight`字段，它属于字段类型和`url`是一样的，不同的是它的`view-name`参数为`snippet-highlight`，也就是说它指向的是名为`snippet-highlight`的 `url parttern`，而不是`snippet-detial`；

由于我们添加了自适应的后缀`format_suffix_patterns`，所以我们仍需要表明`highlight`字段中的任何格式都应该返回`.html`后缀的响应（？？？）；
<br>

## 确保每个 URL patterns 都有命名
使用`hyperlinked API`，我们需要确保对应`url patterns`有命名
1. 根访问点提供`user-list`和`snippet-list`的访问入口
2. `snippet`序列化器引用字段`snippet-highlight`
3. `user`序列化器引用字段`snippet-detial`
4. `snippet`和`user`中的url字段默认引用`{model_name}-detail`，也就是`snippet-detail`和`user-detial`

综上所述，我们在`snippets/urls.py`做如下修改
```python
from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from snippets import views

# API endpoints
urlpatterns = format_suffix_patterns([
    path('', views.api_root),
    path('snippets/',
        views.SnippetList.as_view(),
        name='snippet-list'),
    path('snippets/<int:pk>/',
        views.SnippetDetail.as_view(),
        name='snippet-detail'),
    path('snippets/<int:pk>/highlight/',
        views.SnippetHighlight.as_view(),
        name='snippet-highlight'),
    path('users/',
        views.UserList.as_view(),
        name='user-list'),
    path('users/<int:pk>/',
        views.UserDetail.as_view(),
        name='user-detail')
])
```
最后设置API可视化里单页显示多少个实例
```python
# tutorial/settings.py

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}
