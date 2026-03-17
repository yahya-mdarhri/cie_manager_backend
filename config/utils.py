from management.models import AuditLog

def log_action(user, instance, action, changes=None):
	"""Helper to create audit logs"""
	AuditLog.objects.create(
		user=user,
		model_name=instance.__class__.__name__,
		object_id=instance.pk,
		action=action,
		changes=changes or {},
	)