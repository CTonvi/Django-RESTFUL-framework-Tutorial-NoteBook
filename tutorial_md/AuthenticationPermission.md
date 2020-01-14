目前为止，我们的API没有对编辑或删除代码片段的用户做任何限制，我们应该确保如下几条要求：<br>
1. 每个代码片段实例必须关联它的作者
2. 只有被认证的用户才可以创建代码实例
3. 只有代码片段的作者可以对该代码进行修改或删除
4. 未认证的用户只有只读权限
<br>

## 为代码片段数据模型添加作者信息
为snippet数据模型添加两个新的字段，一个用来存放代码片段作者，另一个存放代码高亮的形式
```python
# snippets/models.py 添加
owner = models.ForeignKey('auth.User', related_name='snippets', on_delete=models.CASCADE)   # 联级删除
highlighted = models.TextField()
```

## 我们还需要确保实例保存的同时构建我们代码高亮形式
```python
# snippets/models.py

from pygments.lexers import get_lexer_by_name
from pygments.formatters.html import HtmlFormatter
from pygments import highlight

# 在原有的基础上重写一下 `Model` 的 `save` 方法
def save(self, *args, **kwargs):
    """
    Use the `pygments` library to create a highlighted HTML
    representation of the code snippet.
    """
    lexer = get_lexer_by_name(self.language)
    linenos = 'table' if self.linenos else False
    options = {'title': self.title} if self.title else {}
    formatter = HtmlFormatter(style=self.style, linenos=linenos,
                              full=True, **options)
    self.highlighted = highlight(self.code, lexer, formatter)
    super(Snippet, self).save(*args, **kwargs)      # 保留原有save的操作
```
现在我们需要去更新我们的数据库，通常我们会使用数据库迁移文件来实现这类的数据库改写；在本次实例中，选择重新建立一个数据库即可
```linux
rm -f db.sqlite3
rm -r snippets/migrations
python manage.py makemigrations snippets
python manage.py migrate
```
创建几个用户来测试我们的API，最快速的方法就是使用 `createsuperuser`
```linux
python manage.py createsuperuser
```
<br>

## 为用户数据模型添加API接口
现在我们已经使用了Django内置的用户模型`User`和几个用户实例，想之前一样，我们需要为该模型添加接口，先写一个序列化器
```python
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    snippets = serializers.PrimaryKeyRelatedField(many=True, queryset=Snippet.objects.all())

    class Meta:
        model = User
        fields = ['id', 'username', 'snippets']
```
由于`snippets`是`User`的从表(反向关系), 所以当我们继承`ModelSerializer`来创建`User`序列化器时，`snippets`不会作为默认字段自动生成，所以我们需要额外声明它;<br>
<br>

另外我们还需要为`User`添加对应的视图功能，我们希望`User`为只读属性，所以使用 `ListAPIView`和`RetrieveAPIView`来构建类视图
```python
# snippets/views.py

from django.contrib.auth.models import User
from snippets.serializers import UserSerializer


class UserList(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer


class UserDetail(generics.RetrieveAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
```
添加URLConf
```python
# snippets/urls.py

path('users/', views.UserList.as_view()),
path('users/<int:pk>/', views.UserDetail.as_view()),
```

## 把这两个模型联系起来
万事具备，就差把两个模型联系起来。目前为止，当我们创建`snippet`实例的时候没有办法关联到`User`，因为这时候`User`并不是`snippet`序列化对象的一部分，它只是请求的属性之一；<br>
这种情况下我们的处理方式是重写`snippet`视图中的`.perform_create()`方法，该方法允许我们管理实例的保存过程，以及处理请求或请求链接中的隐式信息
```python
# snippets/views.py SnippetList
def perform_create(self, serializer):
    serializer.save(owner=self.request.user)
```
`.perfrom_create`是`CreateModelMixin`里的方法，序列化器保存的同时加入字段`owner`
<br>


## 更新Snippet序列化器
现在我们创建`snippet`实例会正确的把`User`关联到一起，接下来我们需要更新`snippet`的序列化器来反映这种关联，增加序列化字段
```python
owner = serializers.ReadOnlyField(source='owner.username')
```
同时还要记得在`Meta`内部类中的`fields`里添加 `'owner'`;<br>
`source`参数用来指定由那个属性来构造该字段；`ReadOnlyField`域是无类型的字段域，和其他有类型的字段域如`CharField`, `BooleanField`相比，它总是只读的，只用于序列化，而不会在执行更新模型实例时被反序列化，我们可以用  `CharField(read_only=True)`达到同样效果；
<br>

## 为视图添加必要的权限
现在我们要求只有认证用户才可以执行`create`,`update`和`delete`snippet实例的操作；<br>
REST framework 提供了许多设计权限的类，来帮助我们约束怎样的请求可以执行视图功能。现在我们尝试使用其中的`IsAuthenticatedOrReadOnly`, 它可以确保已认证的请求拥有读写权限，未认证的请求只有读权限
```python
# snippets/views.py
# 导入所需库
from rest_framework import permissions
```
在`SnippetList`和`SnippetDetail`中添加权限类
```python
permission_classes = [permission.IsAuthenticatedOrReadOnly]
```
我们来看看`IsAuthenticatedOrReadOnly`的源码
```python
class IsAuthenticatedOrReadOnly(BasePermission):
    """
    The request is authenticated as a user, or is a read-only request.
    """
    # 如果请求的方法是安全的或者请求的用户是被认证成功的，则返回True
    def has_permission(self, request, view):
        return bool(
            request.method in SAFE_METHODS or
            request.user and
            request.user.is_authenticated
        )
```
由此看到我们可以随意定制权限类，只要根据自己的业务逻辑来设定`has_permission`的返回值即可
<br>

## 为API浏览器可视化添加登录
目前为止，我们是不能像之前那样直接通过API来创建snippets实例，因为设置用户认证，所以我们需要添加一个登录功能；我们可以直接在项目名目录下的`urls.py`文件中修改urlconf，为browsbale API添加login功能
```python
# tutorial/urls.py

from django.contrib import admin
from django.conf.urls import include
from django.urls import path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('snippets.urls')),
]

urlpatterns += [
    path('api-auth/', include('rest_framework.urls')),
]
```
现在你通过浏览器使用API，右上角就会出现login登录的按钮，使用`createsuperuser`创建的用户登录后，就可以使用`create`创建新的snippet实例了
<br>

## 自定义权限类
现在我们实现了创建snippet实例需要登录认证的功能，但还不够。我们还需要实现只有该代码片段的作者才可以对该代码片段进行修改或删除，这时候我们就需要定制的权限类，首先在snippets文件夹中创建 `permission.py`
```python
# snippets/permission.py

from rest_framework import permissions

class IsOwnerOrReadOnly(permissions.BasePermission):
    """
    Custom permission to only allow owners of an object to edit it.
    """
    def has_object_permission(self, request, view, obj):
         # Read permissions are allowed to any request,
        # so we'll always allow GET, HEAD or OPTIONS requests.
        if request.method in permissions.SAFE_METHODS:
            return True

        # Write permissions are only allowed to the owner of the snippet.
        return obj.owner == request.user
```
然后修改`SnippetDetial`视图类中的权限类
```python
from snippets.permissions import IsOwnerOrReadOnly

permission_classes = [permissions.IsAuthenticatedOrReadOnly, IsOwnerOrReadOnly]
```
现在，只要登录的用户不是代码片段的作者，就无法对其执行修改或删除操作
<br>

# API的认证
我们没有想设置`permission`那样设置`authentication`，所以使用的都是默认的`SessionAuthentication`和`BaseAuthentication`
