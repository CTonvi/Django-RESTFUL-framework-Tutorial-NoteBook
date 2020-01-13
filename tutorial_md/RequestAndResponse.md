## Request对象
REST framework 中的Request对象拓展于Django常规的HttpRequest，提供了灵活的请求解析;<br>
Request对象的核心功能是request.data属性，与常规request.POST类似，但功能大大不同;
```python
request.POST    # 处理POST请求携带的数据且只作用于POST请求
request.data    # 处理所有请求的数据，作用于POST、GET、PATCH等方法
```
<br>

## Response对象
REST framework中的Response对像属于常规`TemplateResponse`，它会获取未进行渲染的内容，通过内容规定向客户端给予正确类型的响应
```python
return Response(data)   # 利用请求中的数据类型进行渲染
```
<br>

## 状态码 Status Codes
使用纯数字标识的状态码通常不方便阅读，容易漏掉错误；REST framework的status模块提供了大量清晰明确的状态码，使用已经封装好的状态码会数字标识清晰很多
```python
from rest_framework import stauts
```
<br>

## 封装视图
REST framework提供两种视图封装方法 <br>
1. 装饰器`@api_view`用于函数视图
2. 类对象`APIView`用于类视图
<br>

这些封装会提供一些功能，比如确保能在视图函数中接受到`Request`实例和在`Response`对象中根据请求去添加上下文；还能在合适的时候返回`405 Method Not Allowed`响应，处理通过`request.data`获取数据时发生的解析异常

<br>

## 开始
使用上文提到过的来重写我们的视图模块
```python
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from snippets.models import Snippet
from snippets.serializers import SnippetSerializer

@api_view(['GET', 'POST'])
def snippet_list(request):
    """
    List all code snippet, or create a new snippet
    """
    if request.method == 'GET':
        snippets = Snippet.objects.all()
        serializer = SnippetSerializer(snippets, many=True)
        return Response(serializer.data)

    elif request.method == 'POST':
        serializer = SnippetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST) 
```
这和我们前一个版本的视图模块相比：
1. 使用了`request.data`减少了解析请求的过程；
2. 使用了`Response`取代了单纯响应json格式的`JSONResponse`，这样可以处理多种数据类型的响应；
3. 使用了`status.HTTP_201_CREATED`取代了纯数字的状态标识；

接下来是单个代码片段实例的视图
```python
@api_view(['GET', 'PUT', 'DELETE'])
def snippet_detail(request, pk):
    """
    Retrieve, update or delete a code snippet.
    """
    try:
        snippet = Snippet.objects.get(pk=pk)
    except Snippet.DoesNotExist:
        return Response(status=status.HTTP_404_NOT_FOUND)

    if request.method == 'GET':
        serializer = SnippetSerializer(snippet)
        return Response(serializer.data)

    elif request.method == 'PUT':
        serializer = SnippetSerializer(snippet, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    elif request.method == 'DELETE':
        snippet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
```
值得注意的是我们一直没有根据内容类型去明确处理请求和响应. `request.data`可以自动处理`json`请求，同时它也可以处理其他类型，同理在处理响应的时候，我们也应该把响应渲染成正确的内容类型
<br>

## 为我们的请求URLs加入可选格式后缀
由于我们的响应不再只处理单一内容类型，所以我们要为API端口添加支持类型后缀的功能，也就是说API端口应该能够处理这样的url请求：`http://example.com/api/items/4.json`<br>
首先需要为视图函数添加`format`参数
```python
def snippet_list(reuqest, format=None):
    ...

def snippet_detail(request, pk, format=None):
    ...
```
然后更新`snippets/urls.py`文件，在现有url配置中添加`format_suffix_patterns`集
```python
from django.urls import path
from rest_framework.urlpatterns import format_suffix_patterns
from snippets import views

urlpatterns = [
    path('snippets/', views.snippet_list),
    path('snippets/<int:pk>', views.snippet_detail),
]

urlpatterns = format_suffix_patterns(urlpatterns)
```
现在我们API终端就拥有灵活处理不同后缀请求的功能了
<br>

## 验证这个功能
运行Django本地服务器，使用https库验证
```python
# 添加格式后缀
http http://127.0.0.1:8000/snippets.json  # JSON suffix
http http://127.0.0.1:8000/snippets.api   # Browsable API suffix

# 修改请求头的 Accept 内容
http http://127.0.0.1:8000/snippets/ Accept:application/json  # Request JSON
http http://127.0.0.1:8000/snippets/ Accept:text/html         # Request HTML

# 修改请求头的 Content-Type
# POST using form data
http --form POST http://127.0.0.1:8000/snippets/ code="print(123)"

{
  "id": 3,
  "title": "",
  "code": "print(123)",
  "linenos": false,
  "language": "python",
  "style": "friendly"
}

# POST using JSON
http --json POST http://127.0.0.1:8000/snippets/ code="print(456)"

{
    "id": 4,
    "title": "",
    "code": "print(456)",
    "linenos": false,
    "language": "python",
    "style": "friendly"
}

