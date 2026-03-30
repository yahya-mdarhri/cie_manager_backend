from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

MAX_DIGITS = 30
DECIMAL_PLACES = 2


class Department(models.Model):
	"""
	Represents a department within the organization.
	"""
	name = models.CharField(max_length=100, unique=True)
	description = models.TextField(blank=True, null=True)
	# manager = models.OneToOneField("users.User", on_delete=models.SET_NULL, null=True, blank=True)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		ordering = ["name"]
		db_table = "departments"
		verbose_name = "Department"
		verbose_name_plural = "Departments"

	def __str__(self):
		return self.name

class Project(models.Model):
	"""
	Represents a project managed by the organization.
	"""
	class ProjectNature(models.TextChoices):
		PURCHASE_ORDER = "Purchase Order", "Purchase Order"
		CONTRACT = "Contract", "Contract"
		AGREEMENT = "Agreement", "Agreement"
		GRANT = "Grant", "Grant"

	class Status(models.TextChoices):
		IN_PROGRESS = "In Progress", "In Progress"
		PAUSED = "Paused", "Paused"
		COMPLETED = "Completed", "Completed"
		CANCELLED = "Cancelled", "Cancelled"

	project_code = models.CharField(max_length=50, unique=True)
	project_name = models.CharField(max_length=255)
	coordinator = models.CharField(max_length=100)
	project_nature = models.CharField(max_length=20, choices=ProjectNature.choices)
	department = models.ForeignKey(Department, on_delete=models.PROTECT, related_name="projects")
	client = models.ForeignKey("Client", on_delete=models.PROTECT, related_name="projects")
	end_date = models.DateField()

	total_budget = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES, default=0)
	committed_budget = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES, default=0)
	remaining_budget = models.DecimalField(
		max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES, editable=False, default=0
	)
	status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)

	# optional budgets by category
	personnel_budget = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES, null=True, blank=True, default=0)
	equipment_budget = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES, null=True, blank=True, default=0)
	subcontracting_budget = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES, null=True, blank=True, default=0)
	mobility_budget = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES, null=True, blank=True, default=0)
	consumables_budget = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES, null=True, blank=True, default=0)
	other_budget = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES, null=True, blank=True, default=0)

	agreement_number = models.CharField(max_length=50, null=True, blank=True)
	client_name = models.CharField(max_length=100, null=True, blank=True)
	contract_documents = models.FileField(upload_to="projects_contracts/", null=True, blank=True)

	# important project dates
	signature_date = models.DateField(null=True, blank=True)
	needs_expression_date = models.DateField(null=True, blank=True)
	client_po_date = models.DateField(null=True, blank=True)
	cg_validation_date = models.DateField(null=True, blank=True)
	da_creation_date = models.DateField(null=True, blank=True)
	purchase_request_date = models.DateField(null=True, blank=True)
	uir_po_send_date = models.DateField(null=True, blank=True)
	uir_delivery_date = models.DateField(null=True, blank=True)
	invoicing_date = models.DateField(null=True, blank=True)
	payment_received_date = models.DateField(null=True, blank=True)

	description = models.TextField(blank=True, null=True)
	objective = models.TextField(blank=True, null=True)
	partners = models.TextField(blank=True, null=True)
	risks = models.TextField(blank=True, null=True)

	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "projects"
		ordering = ["project_code"]
		verbose_name = "Project"
		verbose_name_plural = "Projects"

	def save(self, *args, **kwargs):
		# auto calc remaining budget
		self.remaining_budget = self.total_budget - self.committed_budget
		super().save(*args, **kwargs)

	def __str__(self):
		return f"{self.project_code} - {self.project_name}"

class Expense(models.Model):
	"""
	Represents an expense for a project.
	"""
	class Category(models.TextChoices):
		PERSONNEL = "Personnel", "Personnel"
		EQUIPMENT = "Equipment", "Equipment"
		SUBCONTRACTING = "Subcontracting", "Subcontracting"
		MOBILITY = "Mobility", "Mobility"
		CONSUMABLES = "Consumables", "Consumables"
		OTHER = "Other", "Other"

	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="expenses")
	amount = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES, default=0)
	expense_date = models.DateField()
	category = models.CharField(max_length=20, choices=Category.choices)
	supplier = models.CharField(max_length=255, null=True, blank=True)
	invoice_reference = models.CharField(max_length=255, null=True, blank=True)
	description = models.TextField(null=True, blank=True)
	document_path = models.FileField(upload_to="expenses/", null=True, blank=True)
	payment_date = models.DateField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "expenses"
		ordering = ["-expense_date"]
		verbose_name = "Expense"
		verbose_name_plural = "Expenses"

	def __str__(self):
		return f"{self.project.project_code} - {self.category} - {self.amount}"

class PaymentReceived(models.Model):
	"""
	Represents a payment received for a project.
	"""
	class PaymentType(models.TextChoices):
		BANK_TRANSFER = "Bank Transfer", "Bank Transfer"
		CHECK = "Check", "Check"
		CASH = "Cash", "Cash"

	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="payments_received")
	amount = models.DecimalField(max_digits=MAX_DIGITS, decimal_places=DECIMAL_PLACES, default=0)
	payment_received_date = models.DateField()
	payment_type = models.CharField(max_length=20, choices=PaymentType.choices)
	payment_reference = models.CharField(max_length=100, null=True, blank=True)
	description = models.TextField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "payments_received"
		ordering = ["-payment_received_date"]
		verbose_name = "Payment Received"
		verbose_name_plural = "Payments Received"

	def __str__(self):
		return f"{self.project.project_code} - {self.amount} ({self.payment_type})"

from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

class ActionLogs(models.Model):
	ACTION_CHOICES = [
		("CREATE", "Create"),
		("UPDATE", "Update"),
		("DELETE", "Delete"),
	]

	user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

	# Generic relation to any model
	content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
	object_id = models.CharField(max_length=255)
	content_object = GenericForeignKey("content_type", "object_id")

	action = models.CharField(max_length=10, choices=ACTION_CHOICES)
	changes = models.JSONField(null=True, blank=True)  # {"field": {"old": x, "new": y}}
	ip_address = models.GenericIPAddressField(null=True, blank=True)  # track source
	user_agent = models.TextField(null=True, blank=True)  # track client
	timestamp = models.DateTimeField(auto_now_add=True)

	class Meta:
		verbose_name = "Action Log"
		verbose_name_plural = "Action Logs"
		db_table = "action_logs"
		ordering = ["-timestamp"]


class ProjectSteps(models.Model):
	"""
	Represents the steps or milestones of a project.
	"""

	project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="steps")
	name = models.CharField(max_length=255)
	description = models.TextField(null=True, blank=True)
	start_date = models.DateField(null=True, blank=True)
	end_date = models.DateField(null=True, blank=True)
	execution_status = models.BooleanField(default=False)
	execution_comments = models.TextField(null=True, blank=True)
	execution_proof = models.FileField(upload_to="project_steps/", null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)

	class Meta:
		db_table = "project_steps"
		ordering = ["-created_at"]
		verbose_name = "Project Step"
		verbose_name_plural = "Project Steps"


class Client(models.Model):
	name = models.CharField(max_length=255)
	registration_number = models.CharField(max_length=100, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "clients"
		ordering = ["name"]
		verbose_name = "Client"
		verbose_name_plural = "Clients"

	def __str__(self):
		return f"{self.name} ({self.registration_number})"


class Supplier(models.Model):
	name = models.CharField(max_length=255)
	registration_number = models.CharField(max_length=100, unique=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		db_table = "suppliers"
		ordering = ["name"]
		verbose_name = "Supplier"
		verbose_name_plural = "Suppliers"

	def __str__(self):
		return f"{self.name} ({self.registration_number})"