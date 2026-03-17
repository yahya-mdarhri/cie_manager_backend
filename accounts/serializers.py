from rest_framework import serializers
from django.contrib.auth import authenticate
from .models import User

class UserSerializer(serializers.ModelSerializer):

	class Meta:
		model = User
		fields = ["id", "first_name", "last_name", "username", "email", "role", "department"]
		required_fields = ["first_name", "last_name", "username", "email"]
		read_only_fields = ["id", "role", "department", "is_active", "is_staff", "is_superuser", "password"]

class LoginSerializer(serializers.Serializer):
	email = serializers.EmailField()
	password = serializers.CharField(write_only=True)

	def validate(self, data):
		user = authenticate(username=data["email"], password=data["password"])
		if not user:
			raise serializers.ValidationError("Invalid credentials")
		data["user"] = user
		return data