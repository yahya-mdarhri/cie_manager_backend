from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
	email = models.EmailField(unique=True)

	class Role(models.TextChoices):
		DIRECTOR = "director", "Director"
		DEPARTMENT_MANAGER = "department_manager", "Department Manager"
		USER= "user", "User"

	role = models.CharField(
		max_length=30,
		choices=Role.choices,
		default=Role.USER,
		help_text="User role in the cie manager"
	)
	department = models.ForeignKey(
		'management.Department',
		on_delete=models.SET_NULL,
		null=True,
		blank=True,
		related_name='managers',
		help_text="Department for department managers"
	)

	USERNAME_FIELD = "email"
	REQUIRED_FIELDS = ["username"]

	class Meta(AbstractUser.Meta):
		db_table = "users"
		ordering = ["id"]
		verbose_name = "User"
		verbose_name_plural = "Users"

	def __str__(self):
		return f"{self.email}"

	def is_director(self):
		return self.role == User.Role.DIRECTOR

	def is_department_manager(self):
		return self.role == User.Role.DEPARTMENT_MANAGER

	def is_user(self):
		return self.role == User.Role.USER

	def has_active_role(self):
		return self.role in {User.Role.DIRECTOR, User.Role.DEPARTMENT_MANAGER}

	def setDepartment(self, department):
		# If the user is not a director, set them as a department manager
		self.role = self.Role.DEPARTMENT_MANAGER
		self.save()
		# Assign the department if the user is a department manager
		if self.is_department_manager():
			self.department = department
			self.save()