from accounts.models import User

def has_permission(user, dep = None):
	"""
		Check if a user has permission, optionally considering object scope.
	"""

	# Check user role
	if user.role not in {User.Role.DIRECTOR, User.Role.DEPARTMENT_MANAGER}:
		return False

	# Check for department managers
	if user.role == User.Role.DEPARTMENT_MANAGER:
		# Ensure the user owned this department
		if dep is None:
			return False
		# Ensure the belongs to the user's department
		if user.department != dep:
			return False
	return True
