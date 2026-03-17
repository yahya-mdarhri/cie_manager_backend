from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from management.models import Expense
from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from django.forms.models import model_to_dict
from django.contrib.contenttypes.models import ContentType

from .models import ActionLogs
from .middleware import get_current_user  # we’ll add this to capture user

import datetime
import decimal

ALLOWED_APPS = ["management", "accounts"]

def should_not_log(sender):
    """Only log models from management or accounts apps"""
    return (
        sender._meta.app_label not in ALLOWED_APPS
        or sender == ActionLogs
    )

def to_serializable(value):
	if isinstance(value, (datetime.date, datetime.datetime)):
		return value.isoformat()
	if isinstance(value, decimal.Decimal):
		return float(value)
	if hasattr(value, "pk"):  # e.g. ForeignKey objects
		return str(value.pk)
	return str(value)  # fallback

def create_log(instance, action, changes=None):
	"""Helper to create ActionLogs entries."""


	user = get_current_user()
	content_type = ContentType.objects.get_for_model(instance.__class__)

	# Ensure changes dict is JSON serializable
	serializable_changes = None
	if changes is not None:
		serializable_changes = {
			key: (
				{k: to_serializable(v) for k, v in value.items()}
				if isinstance(value, dict)
				else to_serializable(value)
			)
			for key, value in changes.items()
		}

	ActionLogs.objects.create(
		user=user if user and user.is_authenticated else None,
		content_type=content_type,
		object_id=str(instance.pk),
		action=action,
		changes=serializable_changes,
	)


@receiver(post_save)
def log_create(sender, instance, created, **kwargs):
	if should_not_log(sender):
		return

	if created:
		# Log CREATE
		create_log(instance, "CREATE", changes={"new": model_to_dict(instance)})
	else:
		pass # Log UPDATE done in pre_save


@receiver(pre_save)
def log_update(sender, instance, **kwargs):
	if should_not_log(sender):
		return

	try:
		old_instance = sender.objects.get(pk=instance.pk)
	except sender.DoesNotExist:
		# Object is new, so we skip logging here
		return

	old_data = model_to_dict(old_instance)
	new_data = model_to_dict(instance)

	# Determine what has changed
	changes = {}
	for field in new_data.keys():
		old_value = old_data.get(field)
		new_value = new_data.get(field)
		if old_value != new_value:
			changes[field] = {
				"old": to_serializable(old_value),
				"new": to_serializable(new_value),
			}

	if changes:
		create_log(instance, "UPDATE", changes=changes)

@receiver(post_delete)
def log_delete(sender, instance, **kwargs):
	if should_not_log(sender):
		return

	create_log(
		instance,
		"DELETE",
		changes={"old": model_to_dict(instance), "new": None},
	)


@receiver(post_save, sender=Expense)
def update_project_budget_on_save(sender, instance, created, **kwargs):
	if created:
		instance.project.committed_budget += instance.amount
		instance.project.save()

@receiver(post_delete, sender=Expense)
def update_project_budget_on_delete(sender, instance, **kwargs):
	instance.project.committed_budget -= instance.amount
	instance.project.save()