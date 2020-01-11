1. 首先使用pipenv搭建开发环境，这样能独立于其他项目
```python
pipenv shell
pipenv install django
pipenv install djangorestframework
pipenv install pygements    # 使用pygements实现代码片段的高亮
```
Tip: 使用exit可以退出pipenv的虚拟环境

## Getting Start
创建项目
```python 
django-admin startproject tutorial
cd tutorial
```
创建应用
```
python mange.py startapp snippets
```
项目开始我们需要在 `tutorial/setting.py` 中的 `INSTALLED_APPS` 添加app `snippets`和`rest_framework`
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'snippets',
]
```

## 最基本的，创建我们的数据模型
项目需要实现的功能是运行、存储和修改python代码片段，创建一个`Snippet`数据模型
```python
# snippets/models.py

from django.db import models
from pygments.lexers import get_all_lexers
from pygments.styles import get_all_styles

# 代码高亮相关
LEXERS = [item for item in get_all_lexers() if item[1]]
LANGUAGE_CHOICES = sorted([(item[1][0], item[0]) for item in LEXERS])
STYLE_CHOICES = sorted([(item, item) for item in get_all_styles()])


class Snippet(models.Model):
    created = models.DateTimeField(auto_now_add=True)                   # 创建日期，固定为创建时间，不变
    title = models.CharField(max_length=100, blank=True, default='')    # 代码片段标题，可空，默认为空
    code = models.TextField()                                           # 代码内容  
    linenos = models.BooleanField(default=False)                        # 显示行号
    language = models.CharField(choices=LANGUAGE_CHOICES, default='python', max_length=100)
    style = models.CharField(choices=STYLE_CHOICES, default='friendly', max_length=100)     

    class Meta:
        ordering = ['created']      # 由创建时间进行排序
```
然后我们根据数据模型生成迁移文件并迁移到数据库中
```python
python manage.py makemigrations snippets    
python manage.py migrate
```

## 创建序列化器
序列化器提供将Snippet实例序列化和反序列成Json形式数据的方法，在Snippet应用目录中创建`serializers.py`
```python
# snippet/serializers.py

from rest_framework import serializers
from snippets.models import Snippet, LANGUAGE_CHOICES, STYLE_CHOICES


class SnippetSerializer(serializers.Serializer):

    # 定义需要被序列化/反序列化的字段(fields)
    id = serializers.IntegerField(read_only=True)
    title = serializers.CharField(required=False, allow_blank=True, max_length=100)
    code = serializers.CharField(style={'base_template': 'textarea.html'})
    linenos = serializers.BooleanField(required=False)
    language = serializers.ChoiceField(choices=LANGUAGE_CHOICES, default='python')
    style = serializers.ChoiceField(choices=STYLE_CHOICES, default='friendly')

    # 当self.instance == None， 执行serializer.save() 
    def create(self, validated_data):
        """
        Create and return a new `Snippet` instance, given the validated data.
        """
        return Snippet.objects.create(**validated_data)

    # 当self.instance != None, 执行serializer.save()
    def update(self, instance, validated_data):
        """
        Update and return an existing `Snippet` instance, given the validated data.
        """
        instance.title = validated_data.get('title', instance.title)
        instance.code = validated_data.get('code', instance.code)
        instance.linenos = validated_data.get('linenos', instance.linenos)
        instance.language = validated_data.get('language', instance.language)
        instance.style = validated_data.get('style', instance.style)
        instance.save()
        return instance
```
第一部分定义需要被序列化或反序列化的字段； 可以观察到的是，`serializer`的字段定义和 `Django Form` 的非常相似，包括很多字段定义中的检验参数，比如 `required`, `max_length`, `default`等；我们还可以通过`style`参数定义该字段通过可视化API查看时呈现的方式，上面使用的`style={'base_template':'textarea.html'}`中，`textarea.html`是drf自带的显示模板，等同于`Form`中的 `widget=widgets.Textarea`，渲染到html中就是textarea的文本框<br>
第二部分的 `create` 和 `update` 方法会在执行 `serializer.save()` 时执行，至于是创建还是修改，则取决于创建该序列化器实例时，有没有传进去模型实例参数，看下面的源码可知
```python
# rest_framework/serializers.py 类BaseSerializer的代码片段

if self.instance is not None:
    self.instance = self.update(self.instance, validated_data)
    assert self.instance is not None, (
        '`update()` did not return an object instance.'
    )
else:
    self.instance = self.create(validated_data)
    assert self.instance is not None, (
        '`create()` did not return an object instance.'
    )
```

## 如何使用序列化器实现序列化和反序列化
我们通过 `Django shell` 来使用serializer
```python
python manage.py shell
```
创建两个Snippet实例
```python
from snippets.models import Snippet
from snippets.serializers import SnippetSerializer
from rest_framework.renderers import JSONRenderer
from rest_frameword.parsers import JSONParser

snippet = Snippet(code='foo = "bar"\n')
snippet.save()
snippet = Snippet(code='print("hello, world")\n')
snippet.save()
```
序列化一个实例，观察序列化后的数据显示以及数据类型
```python
serializer = SnippetSerializer(snippet)
serializer.data
# {'id': 2, 'title': '', 'code': 'print("hello, world")\n', 'linenos': False, 'language': 'python', 'style': 'friendly'}
type(serializer.data)
# <class 'rest_framework.utils.serializer_helpers.ReturnDict'>
```
可以看到序列化后的数据类型为`rest_framework`内的`ReturnDict`，我们需要将它渲染为python本地可用以及JSON格式的数据,返回到客户端供使用
```python
content = JSONRenderer().render(serializer.data)
content
# b'{"id": 2, "title": "", "code": "print(\\"hello, world\\")\\n", "linenos": false, "language": "python", "style": "friendly"}'
type(conent)
# <class 'bytes'>
```
对于客户端传上来的JSON格式数据，我们可以如下操作使用数据对实例的创建或修改
```python
import io

stream = io.BytesIO(content)
data = JSONParser().parse(stream)
serializer = SnippetSerializer(data=data)
serializer.is_valid()
# True 必须要在验证后才能读取反序列化后的数据，也就是被整理过的数据
serializer.validate_data
# OrderedDict([('title', ''), ('code', 'print("hello, world")\n'), ('linenos', False), ('language', 'python'), ('style', 'friendly')])
serializer.save()
# <Snippet: Snippet object>
```

## 序列化查询集
我们也可以序列化查询集中所有的实例，而不只是单单一个实例。通过添加参数 `many=True`来实现
```python
serializer = SnippetSerializer(Snippet.objects.all(), manay=True)
serializer.data
# [OrderedDict([('id', 1), ('title', ''), ('code', 'foo = "bar"\n'), ('linenos', False), ('language', 'python'), ('style', 'friendly')]), OrderedDict([('id', 2), ('title', ''), ('code', 'print("hello, world")\n'), ('linenos', False), ('language', 'python'), ('style', 'friendly')]), OrderedDict([('id', 3), ('title', ''), ('code', 'print("hello, world")'), ('linenos', False), ('language', 'python'), ('style', 'friendly')])]
```

## 使用ModelSerializers来简化定义序列化器
我们在上文中定义的Snippet序列化器和数据模型Snippet有着紧密的关联性，rest-framework为我们提供了一个普遍适用与创建serializer的类 `ModelSerializers` ，由此来简化代码， 我们创建一个继承了`ModelSerializers`的序列化器
```python
# snippets/serializers.py

class SnippetModelSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Snippet
        fields = ['id', 'title', 'code', 'linenos', 'language', 'style']
```
通过shell查看具体的字段是如何建立的
```python
from snippets.serializers import SnippetModelSerializer
serializer = SnippetModelSerializer()
print(repr(serializer))
# SnippetModelSerializer():
#    id = IntegerField(label='ID', read_only=True)
#    title = CharField(allow_blank=True, max_length=100, required=False)
#    code = CharField(style={'base_template': 'textarea.html'})
#    linenos = BooleanField(required=False)
#    language = ChoiceField(choices=[('Clipper', 'FoxPro'), ('Cucumber', 'Gherkin'), ('RobotFramework', 'RobotFramework'), ('abap', 'ABAP'), ('ada', 'Ada')...
#    style = ChoiceField(choices=[('autumn', 'autumn'), ('borland', 'borland'), ('bw', 'bw'), ('colorful', 'colorful')...
```
我们可以发现使用ModelSerializer会根据 `model` 的模型数据来创建 `fields` 中提供的字段，同时包括默认的 `update()` 和 `create()` 方法，与上文中的 `SnippetSerializer` 实现相同，但代码更加简洁

## 结合Django常规视图来使用序列化器
编辑视图文件 `snippets/views.py`
```python
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.parsers import JSONParser
from snippets.models import Snippet
from snippets.serializers import SnippetSerializer
```
写一个能实现返回所有snippet实例和创建snippet实例功能的视图
```python
@csrf_exempt
def snippet_list(request):
    """
    List all code snippets, or create a new snippet.
    """
    if request.method == 'GET':
        snippets = Snippet.objects.all()
        serializer = SnippetSerializer(snippets, many=True)
        return JsonResponse(serializer.data, safe=False)

    elif request.method == 'POST':
        data = JSONParser().parse(request)
        serializer = SnippetSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data, status=201)
        return JsonResponse(serializer.errors, status=400)
```
使用`@csrf_exempt`装饰器是为了跳过 `CSRF TOKEN认证`，因为客户端还没写，正常情况下 `CSRF认证`是必须的;<br>
`JsonResponse()`中添加参数`safe=False`可以让其接受非字典类型的数据;<br><br>
再写一个能实现一些作用单独实例的请求，比如获取、更新或者删除
```python
@csrf_exempt
def snippet_detail(request, pk):
    """
    Retrieve, update or delete a code snippet.
    """
    # 根据传入的primary key获取实例
    try:
        snippet = Snippet.objects.get(pk=pk)
    except Snippet.DoesNotExist:
        return HttpResponse(status=404)

    if request.method == 'GET':
        serializer = SnippetSerializer(snippet)
        return JsonResponse(serializer.data)

    elif request.method == 'PUT':
        data = JSONParser().parse(request)
        serializer = SnippetSerializer(snippet, data=data)
        if serializer.is_valid():
            serializer.save()
            return JsonResponse(serializer.data)
        return JsonResponse(serializer.errors, status=400)

    elif request.method == 'DELETE':
        snippet.delete()
        return HttpResponse(status=204)
```
最后就是把视图函数和url对接起来
```python

# snippets/urls.py

from django.urls import path
from snippets import views

urlpartens = [
    path('snippets/', views.snippet_list),
    path('snippets/<int:pk>/', views.snippet_detail),
]
```
```python
# tutorial/urls.py

from django.urls import path, include

urlpatterns = [
    path('', include('snippets.urls')),
]
```
还需要注意的是，目前还没有添加处理发送错误格式JSON数据和处理视图不存在的请求方法，所以当上述两种情况出现时，会出现 `500 server error` 的响应

## 测试 WEB API
首先运行Django自带的服务器
```
python manage.py runserver
```
使用`httpie`库来检验API是否可用
```
pip install httpie
```
获取全部代码片段的API:
```python
http http://127.0.0.1:8000/snippets/

HTTP/1.1 200 OK
...
[
  {
    "id": 1,
    "title": "",
    "code": "foo = \"bar\"\n",
    "linenos": false,
    "language": "python",
    "style": "friendly"
  },
  {
    "id": 2,
    "title": "",
    "code": "print(\"hello, world\")\n",
    "linenos": false,
    "language": "python",
    "style": "friendly"
  }
]
```
根据pk获取某个代码片段实例
```python
http http://127.0.0.1:8000/snippets/2/

HTTP/1.1 200 OK
...
{
  "id": 2,
  "title": "",
  "code": "print(\"hello, world\")\n",
  "linenos": false,
  "language": "python",
  "style": "friendly"
}
```