
from rest_framework.response import Response
from rest_framework import status,viewsets
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.tokens import RefreshToken

from accounts.models import User
from management.pagination import CustomPagination
from .serializers import LoginSerializer, UserSerializer

from django.conf import settings

class MeView(viewsets.ViewSet):

	def retrieve(self, request):
		return Response(UserSerializer(request.user).data, status=status.HTTP_200_OK)

	def update(self, request):
		serializer = UserSerializer(request.user, data=request.data, partial=True)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_200_OK)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class LoginView(viewsets.ViewSet):
	authentication_classes = []
	permission_classes = [AllowAny]

	def create(self, request):
		serializer = LoginSerializer(data=request.data)
		serializer.is_valid(raise_exception=True)
		user = serializer.validated_data["user"]
		refresh = RefreshToken.for_user(user)
		response = Response({
			"user": UserSerializer(user).data,
			settings.AUTH_COOKIE: str(refresh.access_token),
			"refresh": str(refresh),
		}, status=status.HTTP_200_OK)
		# Set JWT in HttpOnly cookie
		# In production (different frontend/backend domains), cookies must be SameSite=None and Secure for XHR
		samesite_value = "Lax" if settings.DEBUG else "None"
		response.set_cookie(
			key=settings.AUTH_COOKIE,
			value=str(refresh.access_token),
			httponly=True,
			samesite=samesite_value,
			secure=not settings.DEBUG,  # secure only in production
			path="/",
		)
		return response

class LogoutView(viewsets.ViewSet):
	def create(self, request):
		response = Response({"detail": "Logged out"}, status=status.HTTP_200_OK)
		response.delete_cookie("access_token")
		return response


class ListUsersView(viewsets.ViewSet):
	permission_classes = [AllowAny]

	def list(self, request):
		user = request.user
		if not user.is_director():
			return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
		users = User.objects.all()
		paginator = CustomPagination()
		users = paginator.paginate_queryset(users, request)
		serializer = UserSerializer(users, many=True)
		return paginator.get_paginated_response(serializer.data)


class UserCreationView(viewsets.ViewSet):
	permission_classes = [AllowAny]

	def create(self, request):
		user = request.user
		if not user.is_director():
			return Response({"detail": "Not authorized"}, status=status.HTTP_403_FORBIDDEN)
		serializer = UserSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(viewsets.ViewSet):

	def update(self, request):
		user = request.user
		new_password = request.data.get("new_password")
		if not new_password:
			return Response({"detail": "New password is required"}, status=status.HTTP_400_BAD_REQUEST)
		user.set_password(new_password)
		user.save()
		return Response({"detail": "Password updated"}, status=status.HTTP_200_OK)