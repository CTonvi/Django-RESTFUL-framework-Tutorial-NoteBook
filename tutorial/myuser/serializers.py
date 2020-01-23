from rest_framework import serializers, urls
# from snippets.models import Snippet
from myuser.models import MyUser

class MyUserHyperSerializer(serializers.HyperlinkedModelSerializer):
    # snippets = serializers.HyperlinkedRelatedField(many=True, read_only=True)

    class Meta:
        model = MyUser
        fields = ['url', 'id', 'telephone', 'email', 'username', 'password', 'is_active',]

class MyUserRegSerializer(serializers.HyperlinkedModelSerializer):

    class Meta:
        model = MyUser
        fields = ['telephone', 'email', 'username', 'password']
    
    def create(self, validated_data):
        telephone = validated_data['telephone']
        email = validated_data['email']
        username = validated_data['username']
        password = validated_data['password']
        instance = MyUser.objects.create_user(telephone, email, username, password)

        return instance