比函数视图更好的是，类视图允许我们复用业务逻辑，同时让我们的代码保持DRY原则(Don't repeat yourself)
<br>

## 使用类视图重写视图模块
```python
# snippets/views.py

from snippets.models import Snippet
from snippets.serializers import SnippetSerializer
from django.http import Http404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status


class SnippetList(APIView):
    """
    List all snippets, or create a new snippet.
    """
    def get(self, request, format=None):
        snippets = Snippet.objects.all()
        serializer = SnippetSerializer(snippets, many=True)
        return Response(serializer.data)

    def post(self, request, format=None):
    serializer = SnippetSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class SnippetDetail(APIView):
    """
    Retrieve, update or delete a snippet instance.
    """
    def get_object(self, pk):
        try:
            return Snippet.objects.get(pk=pk)
        except Snippet.DoesNotExist:
            raise Http404

    def get(self, request, pk, format=None):
        snippet = self.get_object(pk)
        serializer = SnippetSerializer(snippet)
        return Response(serializer.data)

    def put(self, request, pk, format=None):
        snippet = self.get_object(pk)
        serializer = SnippetSerializer(snippet, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, pk, format=None):
        snippet = self.get_object(pk)
        snippet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
```
同样的，在URLCONF上的配置也要改变
```python
# snippets/urls.py

from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from snippets import views

urlpatterns = [
    path('snippets/', views.SnippetList.as_view()),
    path('snippets/<int:pk>/', views.SnippetDetail.as_view()),
]

urlpatterns = format_suffix_patterns(urlpatterns)
```
大功告成后运行Django本地服务器，这和此前使用函数视图的效果是一致的
<br>

##　使用mixins
使用类视图有一个巨大优势是我们可以很轻易的打包并复用一些通用的功能，比方说 `create\retrieve\update\detele` 这些操作通用于大部分我们创建的数据模型；这些相似的功能可以通过REST framework的`mixin`类进行复用<br>
下面展示如何使用`mixin`
```python
from snippets.models import Snippet
from snippets.serializers import SnippetSerializer
from rest_framework import mixins
from rest_framework import generics

class SnippetList(mixins.ListModelMixin,
                    mixins.CreateModelMixin,
                    generics.GenericAPIView):
    queryset = Snippet.objects.all()    # 定义模型数据查询集
    serializer_class = SnippetSerializer    # 定义序列化器

    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)  # list()由ListModelMixin提供
    
    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)    # create()由CreateModelMixin提供
```
首先设定数据模型和序列化器<br>；
然后继承`GenericAPIView`来构建我们的视图类，`GenericAPIView`提供核心功能，是最基础的类；两个`mixins`类分别提供方法`.list()`和`.create()`函数，在我们的视图类中把`get`方法和`.list()`绑定，把`post`方法和`.create()`绑定即可，简便好用。下面挑一个`ListModelMixin`看看源码
```python
class ListModelMixin:
    """
    List a queryset.
    """
    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
```
从中可以看出有`GenericAPIView`提供的核心功能函数，如`.filter_queryset()`、`.paginate_queryset()`等<br>
同样的，我们也使用类`mixins`来改写一些类视图SnippetDetail
```python
class SnippetDetail(mixins.RetrieveModelMixin,
                    mixins.UpdateModelMixin,
                    mixins.DestroyModelMixin,
                    generics.GenericAPIView):
    queryset = Snippet.objects.all()
    serializer_class = SnippetSerializer

    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)

    def put(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        return self.destroy(request, *args, **kwargs)
```
不同的`mixins`类对应不同的功能
<br>

## 使用 Generic class-based veiws
使用`mixin`类可以方便简洁地复用和重写视图，其实我们还可以更加让代码更简洁，把常会用在一起的`mixin`打包在一起成为一个常用的`mixin`组合类，模块`generic`就封装了混合`mixin`，利用它可以使代码更加简洁；
```python
# snippets/views.py

from snippets.models import Snippet
from snippets.serializers import SnippetSerializer
from rest_framework import generics


class SnippetList(generics.ListCreateAPIView):
    queryset = Snippet.objects.all()
    serializer_class = SnippetSerializer


class SnippetDetail(generics.RetrieveUpdateDestroyAPIView):
    queryset = Snippet.objects.all()
    serializer_class = SnippetSerializer
```
看一眼`ListCreateAPIView`的代码
```python
class ListCreateAPIView(mixins.ListModelMixin,
                        mixins.CreateModelMixin,
                        GenericAPIView):
    """
    Concrete view for listing a queryset or creating a model instance.
    """
    def get(self, request, *args, **kwargs):
        return self.list(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        return self.create(request, *args, **kwargs)
```
很熟悉对不对