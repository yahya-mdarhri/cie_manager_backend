from django.urls import path
from .views import *

urlpatterns = [
	path("me/", MeView.as_view({'get': 'retrieve', 'put': 'update'}), name="me"),
	path("login/", LoginView.as_view({'post': 'create'}), name="login"),
	path("logout/", LogoutView.as_view({'post': 'create'}), name="logout"),
	path("change-password/", ChangePasswordView.as_view({'put': 'update'}), name="change_password"),
	path("users/", ListUsersView.as_view({'get': 'list'}), name="list_users"),
	path("users/create/", UserCreationView.as_view({'post': 'create'}), name="create_user"),
]