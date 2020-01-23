from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.base_user import BaseUserManager

# Create your models here.

# 重写UserManage()
class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, telephone, email, username, password, **extra_fields):
        """
        Create and save a user with given telephone, username, email, and password.
        """
        if not telephone:
            raise ValueError("The given telephone must be set")
        if not password:
            raise ValueError("The given password must be set")
        if not email:
            raise ValueError("The given email must be set")
        if not username:
            raise ValueError("The given username must be set")
        email = self.normalize_email(email)
        user = self.model(telephone=telephone, email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_user(self, telephone=None, email=None, username=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(telephone, email, username, password, **extra_fields)
    
    def create_superuser(self, telephone=None, email=None, username=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(telephone, email, username, password, **extra_fields)

class MyUser(AbstractUser):
    telephone = models.CharField(max_length=11, unique=True)
    # 指定telephone作为USERNAME_FIELD，而不是原来的username字段，所以username要重写
    username = models.CharField(max_length=150, unique=True)

    # 指定username字段名作为USERNAME_FIELD，
    # 使用authenticate函数验证用户时，就可以根据在username字段中使用telephone登录
    USERNAME_FIELD = 'username'
    # USERNAME_FIELD默认为必须字段，另外需要添加必须字段
    REQUIRED_FIELDS = [] 

    # 重新定义Manager对象，在创建user的时候使用telephone和password而不是username和password
    objects = UserManager()

    class Meta:
        db_table = "myusers"
        verbose_name = '用户'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.username

