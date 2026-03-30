import json
from rest_framework import status, viewsets
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.db.models import Q, Sum

from accounts.permissions import has_permission
from accounts.serializers import UserSerializer
from management.models import Department, Project, Expense, PaymentReceived, ActionLogs, ProjectSteps, Client, Supplier
from management.pagination import CustomPagination
from management.serializers import DepartmentSerializer, ProjectSerializer, ExpenseSerializer, PaymentReceivedSerializer, ActionLogsSerializer, ProjectStepsSerializer, ClientSerializer, SupplierSerializer

User = get_user_model()

NO_ACCESS_TO_RESOURCE = {"details": "You do not have permission to view this resource."}
DEPARTMENT_NOT_FOUND  = {"details": "Department not found."}
PROJECT_NOT_FOUND     = {"details": "Project not found."}
EXPENSE_NOT_FOUND     = {"details": "Expense not found."}
NOT_ALLOWED_TO = {"details": "You do not have permission to make this action."}
CLIENT_NOT_FOUND = {"details": "Client not found."}
SUPPLIER_NOT_FOUND = {"details": "Supplier not found."}


def can_view_master_data(user):
	return bool(user and user.is_authenticated)


def get_paginator_with_requested_size(request):
	paginator = CustomPagination()
	requested_size = request.query_params.get("size") or request.query_params.get("page_size")
	if requested_size:
		try:
			value = int(requested_size)
			if value > 0:
				paginator.page_size = min(value, paginator.max_page_size)
		except (TypeError, ValueError):
			pass
	return paginator


def getClient(pk):
	try:
		return Client.objects.get(pk=pk)
	except Client.DoesNotExist:
		return None


def getSupplier(pk):
	try:
		return Supplier.objects.get(pk=pk)
	except Supplier.DoesNotExist:
		return None


def serialize_project_for_master_data(project):
	return {
		"id": project.id,
		"project_code": project.project_code,
		"project_name": project.project_name,
		"status": project.status,
		"total_budget": float(project.total_budget or 0),
		"department": project.department.name if project.department else None,
		"department_id": project.department_id,
	}


def serialize_project_for_records(project):
	if not project:
		return None
	return {
		"id": project.id,
		"project_code": project.project_code,
		"project_name": project.project_name,
		"coordinator": project.coordinator,
		"department": {
			"id": project.department.id,
			"name": project.department.name,
		} if project.department else None,
	}


def get_client_totals_payload(client):
	projects = Project.objects.filter(client_name__iexact=client.name).select_related("department")
	project_rows = []
	total_revenue = 0
	for project in projects:
		project_total = project.payments_received.aggregate(total=Sum("amount")).get("total") or 0
		total_revenue += project_total
		project_rows.append(
			{
				"project_id": project.id,
				"project_code": project.project_code,
				"project_name": project.project_name,
				"department": project.department.name if project.department else None,
				"total_revenue": float(project_total),
			}
		)
	return {
		"total_revenue": float(total_revenue),
		"projects": project_rows,
	}


def get_supplier_totals_payload(supplier):
	projects = Project.objects.filter(expenses__supplier__iexact=supplier.name).distinct().select_related("department")
	project_rows = []
	total_expense = 0
	for project in projects:
		project_total = project.expenses.filter(supplier__iexact=supplier.name).aggregate(total=Sum("amount")).get("total") or 0
		total_expense += project_total
		project_rows.append(
			{
				"project_id": project.id,
				"project_code": project.project_code,
				"project_name": project.project_name,
				"department": project.department.name if project.department else None,
				"total_expense": float(project_total),
			}
		)
	return {
		"total_expense": float(total_expense),
		"projects": project_rows,
	}


def serialize_client_with_metrics(client):
	client_data = ClientSerializer(client).data
	projects = Project.objects.filter(client_name__iexact=client.name).select_related("department")
	total_revenue = 0
	project_items = []
	for project in projects:
		project_items.append(serialize_project_for_master_data(project))
		project_total = project.payments_received.aggregate(total=Sum("amount")).get("total") or 0
		total_revenue += project_total
	client_data["projects"] = project_items
	client_data["total_revenue"] = float(total_revenue)
	return client_data


def serialize_supplier_with_metrics(supplier):
	supplier_data = SupplierSerializer(supplier).data
	projects = Project.objects.filter(expenses__supplier__iexact=supplier.name).distinct().select_related("department")
	total_expense = 0
	project_items = []
	for project in projects:
		project_items.append(serialize_project_for_master_data(project))
		project_total = project.expenses.filter(supplier__iexact=supplier.name).aggregate(total=Sum("amount")).get("total") or 0
		total_expense += project_total
	supplier_data["projects"] = project_items
	supplier_data["total_expense"] = float(total_expense)
	return supplier_data


def normalize_amount(value):
	if value is None:
		return None
	if isinstance(value, (int, float)):
		return value
	text = str(value).strip().replace(" ", "").replace(",", ".")
	try:
		return float(text)
	except (TypeError, ValueError):
		return None


def normalize_expense_category(value):
	if not value:
		return value
	key = str(value).strip().lower()
	mapping = {
		"personnel": Expense.Category.PERSONNEL,
		"equipment": Expense.Category.EQUIPMENT,
		"equipement": Expense.Category.EQUIPMENT,
		"subcontracting": Expense.Category.SUBCONTRACTING,
		"sous-traitance": Expense.Category.SUBCONTRACTING,
		"mobility": Expense.Category.MOBILITY,
		"mobilite": Expense.Category.MOBILITY,
		"mobilité": Expense.Category.MOBILITY,
		"material": Expense.Category.CONSUMABLES,
		"materiel": Expense.Category.CONSUMABLES,
		"matériel": Expense.Category.CONSUMABLES,
		"consumables": Expense.Category.CONSUMABLES,
		"consommables": Expense.Category.CONSUMABLES,
		"other": Expense.Category.OTHER,
		"autre": Expense.Category.OTHER,
	}
	return mapping.get(key, value)


def normalize_payment_type(value):
	if not value:
		return PaymentReceived.PaymentType.BANK_TRANSFER
	key = str(value).strip().lower()
	mapping = {
		"bank transfer": PaymentReceived.PaymentType.BANK_TRANSFER,
		"transfer": PaymentReceived.PaymentType.BANK_TRANSFER,
		"virement": PaymentReceived.PaymentType.BANK_TRANSFER,
		"check": PaymentReceived.PaymentType.CHECK,
		"cheque": PaymentReceived.PaymentType.CHECK,
		"chèque": PaymentReceived.PaymentType.CHECK,
		"cash": PaymentReceived.PaymentType.CASH,
		"especes": PaymentReceived.PaymentType.CASH,
		"espèces": PaymentReceived.PaymentType.CASH,
	}
	return mapping.get(key, value)

def getDepartment(pk):
	try:
		return Department.objects.get(pk=pk)
	except Department.DoesNotExist:
		return None

def getDepartmentProject(dep, proj):
	try:
		return dep.projects.get(pk=proj)
	except Project.DoesNotExist:
		return None

def getProjectExpense(proj, exp):
	try:
		return proj.expenses.get(pk=exp)
	except Expense.DoesNotExist:
		return None

def getDepartmentIfHasAccess(user, pk):
	department = getDepartment(pk)
	if not department:
		return None, Response(
			DEPARTMENT_NOT_FOUND,
			status=status.HTTP_404_NOT_FOUND
		)
	if not has_permission(user, department):
		return None, Response(
			NO_ACCESS_TO_RESOURCE,
			status=status.HTTP_403_FORBIDDEN
		)
	return department, None


class ListDepartmentView(viewsets.ViewSet):

	def list(self, request):
		user = request.user
		# Check if the user has access to all department
		if has_permission(user):
			paginator = CustomPagination()
			departments = Department.objects.all()
			departments = paginator.paginate_queryset(departments, request)
			serializer = DepartmentSerializer(departments, many=True)
			return paginator.get_paginated_response(serializer.data)
		return Response(
			NO_ACCESS_TO_RESOURCE,
			status=status.HTTP_403_FORBIDDEN
		)

class SetDepartmentManagerView(viewsets.ViewSet):

	def update(self, request, dep=None):
		user = request.user
		manger_pk = request.data.get("manager")
		if not manger_pk:
			return Response(
				{"details": "Manager ID is required."},
				status=status.HTTP_400_BAD_REQUEST
			)
		# Check if the department is exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the manager is exist
		try:
			manager = User.objects.get(pk=manger_pk)
		except User.DoesNotExist:
			return Response(
				{"details": "Manager not found."},
				status=status.HTTP_404_NOT_FOUND
			)
		# Check if the manager is not a director
		if not manager.is_user():
			return Response(
				{"details": "A director or a department manager cannot be assigned as a department manager."},
				status=status.HTTP_400_BAD_REQUEST
			)
		manager.setDepartment(department)
		return Response(
			{"details": "Department manager updated."},
			status=status.HTTP_200_OK
		)


class ListDepartmentManagersView(viewsets.ViewSet):

	def list(self, request, dep=None):
		user = request.user
		department, error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		managers = department.managers.filter(role=User.Role.DEPARTMENT_MANAGER)
		paginator = get_paginator_with_requested_size(request)
		managers = paginator.paginate_queryset(managers, request)
		serializer = UserSerializer(managers, many=True)
		return paginator.get_paginated_response(serializer.data)

class GetDepartmentView(viewsets.ViewSet):

	def retrieve(self, request, pk=None):
		user = request.user
		# Check if the department is exist
		department = getDepartment(pk)
		if not department:
			return Response(
				DEPARTMENT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Check if the user has access to this department
		if not has_permission(user,  department):
			return Response(
				NO_ACCESS_TO_RESOURCE,
				status=status.HTTP_403_FORBIDDEN
			)
		serializer = DepartmentSerializer(department)
		return Response(serializer.data)

	def update(self, request, pk=None):
		user = request.user
		# Check if the department is exist
		department = getDepartment(pk)
		if not department:
			return Response(
				DEPARTMENT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Check if the  user has rights to edit the department's details
		if not has_permission(user, department):
			return Response(
				NO_ACCESS_TO_RESOURCE,
				status=status.HTTP_403_FORBIDDEN
			)
		data = request.data.copy()
		manager_ids_raw = data.pop("manager_ids", None)

		def normalize_manager_ids(raw_value):
			if raw_value is None:
				return None
			items = raw_value if isinstance(raw_value, (list, tuple)) else [raw_value]
			normalized = []
			for item in items:
				if item is None:
					continue
				if isinstance(item, (list, tuple)):
					normalized.extend(item)
					continue
				text = str(item).strip()
				if not text:
					continue
				if text.startswith("[") and text.endswith("]"):
					try:
						parsed = json.loads(text)
						if isinstance(parsed, list):
							normalized.extend(parsed)
							continue
					except (TypeError, ValueError):
						pass
				if "," in text:
					normalized.extend(part.strip() for part in text.split(",") if part.strip())
				else:
					normalized.append(text)

			result = []
			for value in normalized:
				try:
					result.append(int(value))
				except (TypeError, ValueError):
					continue
			return list(dict.fromkeys(result))

		manager_ids = normalize_manager_ids(manager_ids_raw)
		if manager_ids is not None and not user.is_director():
			return Response(
				NOT_ALLOWED_TO,
				status=status.HTTP_403_FORBIDDEN
			)

		#Check if the provided details are valid, if yes save them, otherwise no
		serializer = DepartmentSerializer(department, data=data, partial=True)
		if serializer.is_valid():
			serializer.save()
			if manager_ids is not None:
				selected_users = User.objects.filter(id__in=manager_ids)
				selected_ids = set(selected_users.values_list("id", flat=True))
				missing_ids = set(manager_ids) - selected_ids
				if missing_ids:
					return Response(
						{"details": f"Managers not found: {sorted(missing_ids)}"},
						status=status.HTTP_404_NOT_FOUND
					)

				for manager in selected_users:
					if manager.is_director():
						return Response(
							{"details": "A director cannot be assigned as department manager."},
							status=status.HTTP_400_BAD_REQUEST
						)

				department.managers.filter(role=User.Role.DEPARTMENT_MANAGER).exclude(id__in=manager_ids).update(
					role=User.Role.USER,
					department=None,
				)
				for manager in selected_users:
					manager.role = User.Role.DEPARTMENT_MANAGER
					manager.department = department
					manager.save(update_fields=["role", "department"])

			return Response(
				{"details": "Department details updated."},
				status=status.HTTP_200_OK
			)
		return Response(
			serializer.errors,
			status=status.HTTP_400_BAD_REQUEST
		)

	def destroy(self, request, pk=None):
		user = request.user
		# Check if the department is exist
		department = getDepartment(pk)
		if not department:
			return Response(
				DEPARTMENT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Check if the  user has rights to delete the department
		if not has_permission(user, department):
			return Response(
				NO_ACCESS_TO_RESOURCE,
				status=status.HTTP_403_FORBIDDEN
			)
		department.delete()
		return Response(
			{"details": "Department deleted."},
			status=status.HTTP_204_NO_CONTENT
		)


class CreateDepartmentView(viewsets.ViewSet):

	def create(self, request):
		user = request.user
		# Check if the user has permission to create a department
		if not has_permission(user):
			return Response(
				NOT_ALLOWED_TO,
				status=status.HTTP_403_FORBIDDEN
			)
		serializer = DepartmentSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			return Response(
				{"details": "Department created."},
				status=status.HTTP_201_CREATED
			)
		return Response(
			serializer.errors,
			status=status.HTTP_400_BAD_REQUEST
		)


class ListProjectsView(viewsets.ViewSet):

	def list(self, request, pk=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, pk)
		if error_response:
			return error_response
		# Get all projects of this departments
		paginator = CustomPagination()
		projects = department.projects.all()
		projects = paginator.paginate_queryset(projects, request)
		serializer = ProjectSerializer(projects, many=True)
		return paginator.get_paginated_response(serializer.data)


class GetProjectView(viewsets.ViewSet):

	def retrieve(self, request, dep=None, proj=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Get project details
		serializer = ProjectSerializer(project)
		return Response(
			serializer.data,
			status=status.HTTP_200_OK
		)

	def update(self, request, dep=None, proj=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		serializer = ProjectSerializer(project, data=request.data, partial=True)
		# old_data = serializer.data
		#Check if the provided details are valid, if yes save them, otherwise no
		if serializer.is_valid():
			serializer.save()
			# changes = {k: (old_data[k], serializer.data[k]) for k in serializer.data if old_data[k] != serializer.data[k]}
			# if changes:
			# 	log_action(user, project, "UPDATE", changes)
			return Response(
				{"details": "Project details updated."},
				status=status.HTTP_200_OK
			)
		return Response(
			serializer.errors,
			status=status.HTTP_400_BAD_REQUEST
		)

	def destroy(self, request, dep=None, proj=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		project.delete()
		return Response(
			{"details": "Project deleted."},
			status=status.HTTP_204_NO_CONTENT
		)

class CreateProjectView(viewsets.ViewSet):
  
	def create(self, request, dep=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response

		data = request.data.copy()

		def first_value(raw):
			if isinstance(raw, (list, tuple)):
				return raw[0] if raw else None
			return raw

		def normalized_int(raw):
			value = first_value(raw)
			if value is None:
				return None
			text = str(value).strip()
			if not text:
				return None
			try:
				return int(text)
			except (TypeError, ValueError):
				return None

		# Resolve coordinator sent as coordinator_user_id (frontend director flow)
		coordinator_user_id = normalized_int(data.pop("coordinator_user_id", None))
		if coordinator_user_id and not data.get("coordinator"):
			try:
				coordinator_user = User.objects.get(pk=coordinator_user_id)
				full_name = f"{coordinator_user.first_name} {coordinator_user.last_name}".strip()
				data["coordinator"] = full_name or coordinator_user.email or coordinator_user.username
			except User.DoesNotExist:
				return Response(
					{"details": "Coordinator user not found."},
					status=status.HTTP_404_NOT_FOUND
				)
		elif first_value(request.data.get("coordinator_user_id")) and not data.get("coordinator"):
			return Response(
				{"details": "Invalid coordinator user id."},
				status=status.HTTP_400_BAD_REQUEST
			)

		# Resolve client sent as master-data id (frontend sends field `client`)
		client_ref = normalized_int(data.pop("client", None))
		if client_ref:
			try:
				client = Client.objects.get(pk=client_ref)
				data["client"] = client.id
				if not data.get("client_name"):
					data["client_name"] = client.name
			except Client.DoesNotExist:
				return Response(
					{"details": "Client not found."},
					status=status.HTTP_404_NOT_FOUND
				)
		elif first_value(request.data.get("client")) and not data.get("client_name"):
			return Response(
				{"details": "Invalid client id."},
				status=status.HTTP_400_BAD_REQUEST
			)
		elif data.get("client_name") and not data.get("client"):
			client_name = str(data.get("client_name")).strip()
			client = Client.objects.filter(name__iexact=client_name).first()
			if client:
				data["client"] = client.id
				data["client_name"] = client.name
			else:
				return Response(
					{"details": "Client is required and must exist in master data."},
					status=status.HTTP_400_BAD_REQUEST
				)
		elif not data.get("client"):
			return Response(
				{"details": "Client is required."},
				status=status.HTTP_400_BAD_REQUEST
			)

		# Some front versions may send these aliases; normalize and drop unknown keys
		data.pop("client_id", None)
		data.pop("main_supplier", None)

		# Create the project
		serializer = ProjectSerializer(data=data)
		if serializer.is_valid():
			serializer.save(department=department)
			project = serializer.instance
			if "jalons" in request.data:
				try:
					steps_data = request.data["jalons"]
					step_json = json.loads(steps_data)
					for step in step_json.get("jalons", []):
						step_serializer = ProjectStepsSerializer(data=step)
						if step_serializer.is_valid():
							step_serializer.save(project=project)
				except (TypeError, ValueError, AttributeError):
					return Response(
						{"details": "Invalid jalons payload."},
						status=status.HTTP_400_BAD_REQUEST
					)
			return Response(
				{"details": "Project created."},
				status=status.HTTP_201_CREATED
			)
		return Response(
			serializer.errors,
			status=status.HTTP_400_BAD_REQUEST
		)

class ListProjectExpensesView(viewsets.ViewSet):

	def list(self, request, dep=None, proj=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Get all expenses of this project
		paginator = CustomPagination()
		expenses = project.expenses.all()
		paginated_expenses = paginator.paginate_queryset(expenses, request)
		serializer = ExpenseSerializer(paginated_expenses, many=True)
		return paginator.get_paginated_response(serializer.data)

class GetProjectExpenseView(viewsets.ViewSet):

	def retrieve(self, request, dep=None, proj=None, exp=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Check if the expense exists
		expense = getProjectExpense(project, exp)
		if not expense:
			return Response(
				EXPENSE_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Get expense details
		serializer = ExpenseSerializer(expense)
		return Response(
			serializer.data,
			status=status.HTTP_200_OK
		)

	def update(self, request, dep=None, proj=None, exp=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Check if the expense exists
		expense = getProjectExpense(project, exp)
		if not expense:
			return Response(
				EXPENSE_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Update expense details
		serializer = ExpenseSerializer(expense, data=request.data, partial=True)
		if serializer.is_valid():
			serializer.save()
			return Response(
				{"details": "Expense details updated."},
				status=status.HTTP_200_OK
			)
		return Response(
			serializer.errors,
			status=status.HTTP_400_BAD_REQUEST
		)

	def destroy(self, request, dep=None, proj=None, exp=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Check if the expense exists
		expense = getProjectExpense(project, exp)
		if not expense:
			return Response(
				EXPENSE_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		expense.delete()
		return Response(
			{"details": "Expense deleted."},
			status=status.HTTP_204_NO_CONTENT
		)


class CreateProjectExpenseView(viewsets.ViewSet):

	def create(self, request, dep=None, proj=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Create the expense
		data = request.data.copy()
		supplier_ref = data.pop("supplier_ref", None)
		if supplier_ref:
			try:
				supplier = Supplier.objects.get(pk=supplier_ref)
				data["supplier"] = supplier.name
			except Supplier.DoesNotExist:
				return Response(
					{"details": "Supplier not found."},
					status=status.HTTP_404_NOT_FOUND
				)
		data["amount"] = normalize_amount(data.get("amount"))
		data["category"] = normalize_expense_category(data.get("category"))
		data["project"] = project.pk
		if data.get("amount") is None:
			return Response(
				{"details": "Amount is required and must be a valid number."},
				status=status.HTTP_400_BAD_REQUEST
			)
		serializer = ExpenseSerializer(data=data)
		if serializer.is_valid():
			serializer.save(project=project)
			return Response(
				{"details": "Expense created."},
				status=status.HTTP_201_CREATED
			)
		return Response(
			serializer.errors,
			status=status.HTTP_400_BAD_REQUEST
		)


class ListProjectPaymentsReceivedView(viewsets.ViewSet):

	def list(self, request, dep=None, proj=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Get all payments received of this project
		paginator = CustomPagination()
		payments_received = project.payments_received.all()
		payments_received = paginator.paginate_queryset(payments_received, request)
		serializer = PaymentReceivedSerializer(payments_received, many=True)
		return paginator.get_paginated_response(serializer.data)

class GetProjectPaymentReceivedView(viewsets.ViewSet):

	def retrieve(self, request, dep=None, proj=None, pay=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Check if the payment received exists
		try:
			payment_received = project.payments_received.get(pk=pay)
		except PaymentReceived.DoesNotExist:
			return Response(
				{"details": "Payment received not found."},
				status=status.HTTP_404_NOT_FOUND
			)
		# Get payment received details
		serializer = PaymentReceivedSerializer(payment_received)
		return Response(
			serializer.data,
			status=status.HTTP_200_OK
		)

	def update(self, request, dep=None, proj=None, pay=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Check if the payment received exists
		try:
			payment_received = project.payments_received.get(pk=pay)
		except PaymentReceived.DoesNotExist:
			return Response(
				{"details": "Payment received not found."},
				status=status.HTTP_404_NOT_FOUND
			)
		# Update payment received details
		serializer = PaymentReceivedSerializer(payment_received, data=request.data, partial=True)
		if serializer.is_valid():
			serializer.save()
			return Response(
				{"details": "Payment received details updated."},
				status=status.HTTP_200_OK
			)
		return Response(
			serializer.errors,
			status=status.HTTP_400_BAD_REQUEST
		)

	def destroy(self, request, dep=None, proj=None, pay=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Check if the payment received exists
		try:
			payment_received = project.payments_received.get(pk=pay)
		except PaymentReceived.DoesNotExist:
			return Response(
				{"details": "Payment received not found."},
				status=status.HTTP_404_NOT_FOUND
			)
		payment_received.delete()
		return Response(
			{"details": "Payment received deleted."},
			status=status.HTTP_204_NO_CONTENT
		)

class CreateProjectPaymentReceivedView(viewsets.ViewSet):

	def create(self, request, dep=None, proj=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Create the payment received
		data = request.data.copy()
		client_ref = data.pop("client_ref", None)
		if client_ref:
			try:
				client = Client.objects.get(pk=client_ref)
				if not project.client_name:
					project.client_name = client.name
					project.save(update_fields=["client_name", "updated_at"])
			except Client.DoesNotExist:
				return Response(
					{"details": "Client not found."},
					status=status.HTTP_404_NOT_FOUND
				)
		data["amount"] = normalize_amount(data.get("amount"))
		data["payment_type"] = normalize_payment_type(data.get("payment_type"))
		data["project"] = project.pk
		if not data.get("payment_reference"):
			data["payment_reference"] = "REF"
		if data.get("amount") is None:
			return Response(
				{"details": "Amount is required and must be a valid number."},
				status=status.HTTP_400_BAD_REQUEST
			)
		serializer = PaymentReceivedSerializer(data=data)
		if serializer.is_valid():
			serializer.save(project=project)
			return Response(
				{"details": "Payment received created."},
				status=status.HTTP_201_CREATED
			)
		return Response(
			serializer.errors,
			status=status.HTTP_400_BAD_REQUEST
		)



class ListActionLogsView(viewsets.ViewSet):

	def list(self, request):
		user = request.user
		# Check if the user has access to all action logs
		if user.is_director():
			paginator = CustomPagination()
			logs = ActionLogs.objects.all()
			logs = paginator.paginate_queryset(logs, request)
			serializer = ActionLogsSerializer(logs, many=True)
			return paginator.get_paginated_response(serializer.data)
		return Response(
			NO_ACCESS_TO_RESOURCE,
			status=status.HTTP_403_FORBIDDEN
		)


class GetActionLogView(viewsets.ViewSet):

	def retrieve(self, request, pk=None):
		user = request.user
		# Check if the user has access to all action logs
		if not user.is_director():
			return Response(
				NO_ACCESS_TO_RESOURCE,
				status=status.HTTP_403_FORBIDDEN
			)
		# Check if the action log exists
		try:
			log = ActionLogs.objects.get(pk=pk)
		except ActionLogs.DoesNotExist:
			return Response(
				{"details": "Action log not found."},
				status=status.HTTP_404_NOT_FOUND
			)
		serializer = ActionLogsSerializer(log)
		return Response(
			serializer.data,
			status=status.HTTP_200_OK
		)


class ListProjectStepsView(viewsets.ViewSet):

	def list(self, request, dep=None, proj=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Get all steps of this project
		steps = project.steps.all()
		paginator = CustomPagination()
		steps = paginator.paginate_queryset(steps, request)
		serializer = ProjectStepsSerializer(steps, many=True)
		return paginator.get_paginated_response(serializer.data)


class GetProjectStepView(viewsets.ViewSet):
  
	def retrieve(self, request, dep=None, proj=None, step=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Check if the step exists
		try:
			project_step = project.steps.get(pk=step)
		except ProjectSteps.DoesNotExist:
			return Response(
				{"details": "Project step not found."},
				status=status.HTTP_404_NOT_FOUND
			)
		# Get step details
		serializer = ProjectStepsSerializer(project_step)
		return Response(
			serializer.data,
			status=status.HTTP_200_OK
		)

	def update(self, request, dep=None, proj=None, step=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Check if the step exists
		try:
			project_step = project.steps.get(pk=step)
		except ProjectSteps.DoesNotExist:
			return Response(
				{"details": "Project step not found."},
				status=status.HTTP_404_NOT_FOUND
			)
		# Update step details
		serializer = ProjectStepsSerializer(project_step, data=request.data, partial=True)
		if serializer.is_valid():
			serializer.save()
			return Response(
				{"details": "Project step details updated."},
				status=status.HTTP_200_OK
			)
		return Response(
			serializer.errors,
			status=status.HTTP_400_BAD_REQUEST
		)

	def destroy(self, request, dep=None, proj=None, step=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Check if the step exists
		try:
			project_step = project.steps.get(pk=step)
		except ProjectSteps.DoesNotExist:
			return Response(
				{"details": "Project step not found."},
				status=status.HTTP_404_NOT_FOUND
			)
		project_step.delete()
		return Response(
			{"details": "Project step deleted."},
			status=status.HTTP_204_NO_CONTENT
		)

class CreateProjectStepView(viewsets.ViewSet):
	
	def create(self, request, dep=None, proj=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Create the project step
		serializer = ProjectStepsSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save(project=project)
			return Response(
				{"details": "Project step created."},
				status=status.HTTP_201_CREATED
			)
		return Response(
			serializer.errors,
			status=status.HTTP_400_BAD_REQUEST
		)

class ListAllProjectView(viewsets.ViewSet):

	def list(self, request):
		user = request.user
		# Check if the user has access to all projects
		if user.is_director():
			paginator = CustomPagination()
			projects = Project.objects.all()
			projects = paginator.paginate_queryset(projects, request)
			serializer = ProjectSerializer(projects, many=True)
			return paginator.get_paginated_response(serializer.data)
		return Response(
			NO_ACCESS_TO_RESOURCE,
			status=status.HTTP_403_FORBIDDEN
		)


class ListAllExpensesView(viewsets.ViewSet):

	def list(self, request):
		user = request.user
		# Check if the user has access to all expenses
		if user.is_director():
			paginator = CustomPagination()
			expenses = Expense.objects.select_related("project", "project__department").all()
			expenses = paginator.paginate_queryset(expenses, request)
			serializer = ExpenseSerializer(expenses, many=True)
			data = serializer.data
			for idx, expense in enumerate(expenses):
				data[idx]["project"] = serialize_project_for_records(expense.project)
			return paginator.get_paginated_response(data)
		return Response(
			NO_ACCESS_TO_RESOURCE,
			status=status.HTTP_403_FORBIDDEN
		)

class ListAllPaymentsReceivedView(viewsets.ViewSet):

	def list(self, request):
		user = request.user
		# Check if the user has access to all payments received
		if user.is_director():
			paginator = CustomPagination()
			payments_received = PaymentReceived.objects.select_related("project", "project__department").all()
			payments_received = paginator.paginate_queryset(payments_received, request)
			serializer = PaymentReceivedSerializer(payments_received, many=True)
			data = serializer.data
			for idx, payment in enumerate(payments_received):
				data[idx]["project"] = serialize_project_for_records(payment.project)
			return paginator.get_paginated_response(data)
		return Response(
			NO_ACCESS_TO_RESOURCE,
			status=status.HTTP_403_FORBIDDEN
		)


class ListAllFiltersView(viewsets.ViewSet):

	def list(self, request):
		user = request.user
		if not (user.is_director() or user.is_department_manager()):
			return Response(
				NO_ACCESS_TO_RESOURCE,
				status=status.HTTP_403_FORBIDDEN
			)

		departments = list(
			Department.objects.order_by("name").values_list("name", flat=True).distinct()
		)
		coordinators = list(
			Project.objects.exclude(coordinator__isnull=True)
			.exclude(coordinator__exact="")
			.order_by("coordinator")
			.values_list("coordinator", flat=True)
			.distinct()
		)
		expense_categories = list(
			Expense.objects.exclude(category__isnull=True)
			.exclude(category__exact="")
			.order_by("category")
			.values_list("category", flat=True)
			.distinct()
		)
		payment_types = list(
			PaymentReceived.objects.exclude(payment_type__isnull=True)
			.exclude(payment_type__exact="")
			.order_by("payment_type")
			.values_list("payment_type", flat=True)
			.distinct()
		)
		suppliers = list(
			Supplier.objects.order_by("name").values_list("name", flat=True).distinct()
		)
		clients = list(
			Client.objects.order_by("name").values_list("name", flat=True).distinct()
		)

		return Response(
			{
				"departments": departments,
				"coordinators": coordinators,
				"expense_categories": expense_categories,
				"payment_types": payment_types,
				"suppliers": suppliers,
				"clients": clients,
			},
			status=status.HTTP_200_OK
		)

class ExecuteProjectStepView(viewsets.ViewSet):

	def execute(self, request, dep=None, proj=None, step=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Check if the project exists
		project = getDepartmentProject(department, proj)
		if not project:
			return Response(
				PROJECT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		# Check if the step exists
		try:
			project_step = project.steps.get(pk=step)
		except ProjectSteps.DoesNotExist:
			return Response(
				{"details": "Project step not found."},
				status=status.HTTP_404_NOT_FOUND
			)
		# Mark the step as executed
		if project_step.execution_status:
			return Response(
				{"details": "Project step is already marked as executed."},
				status=status.HTTP_400_BAD_REQUEST
			)
		data = request.data.copy()
		if not data.get("execution_proof"):
			return Response(
				{"details": "Execution proof is required."},
				status=status.HTTP_400_BAD_REQUEST
			)
		data["execution_status"] = True
		serializer = ProjectStepsSerializer(project_step, data=data, partial=True)
		if serializer.is_valid():
			serializer.save()
		return Response(
			{"details": "Project step marked as executed."},
			status=status.HTTP_200_OK
		)

class DirectorDashboardView(viewsets.ViewSet):

	def retrieve(self, request):
		user = request.user
		# Check if the user has access to the dashboard
		if not user.is_director():
			return Response(
				NO_ACCESS_TO_RESOURCE,
				status=status.HTTP_403_FORBIDDEN
			)
		# Calculate dashboard metrics
		total_projects = Project.objects.count()
		total_budget = sum(project.total_budget for project in Project.objects.all())
		committed_budget = sum(project.committed_budget for project in Project.objects.all())
		remaining_budget = total_budget - committed_budget

		status_counts = {
			'in_progress': Project.objects.filter(status=Project.Status.IN_PROGRESS).count(),
			'on_hold': Project.objects.filter(status=Project.Status.PAUSED).count(),
			'completed': Project.objects.filter(status=Project.Status.COMPLETED).count(),
			'canceled': Project.objects.filter(status=Project.Status.CANCELLED).count(),
		}

		dashboard_data = {
			"active_projects": {
				"number": total_projects,
				"percentage_change": "+0%"  # Placeholder for percentage change logic
			},
			"total_budget": {
				"amount": f"{total_budget} MAD",
				"percentage_change": "+0%"  # Placeholder for percentage change logic
			},
			"committed_budget": {
				"amount": f"{committed_budget} MAD",
				"percentage_change": "+0%"  # Placeholder for percentage change logic
			},
			"remaining_budget": {
				"amount": f"{remaining_budget} MAD",
				"percentage_change": "+0%"  # Placeholder for percentage change logic
			},
			"projects_by_status": status_counts,
		}
		
		return Response(dashboard_data, status=status.HTTP_200_OK)

class DepartmentDashboardView(viewsets.ViewSet):

	def retrieve(self, request, dep=None):
		user = request.user
		# Check if the department exist, and has access
		department , error_response = getDepartmentIfHasAccess(user, dep)
		if error_response:
			return error_response
		# Calculate dashboard metrics
		total_projects = department.projects.count()
		total_budget = sum(project.total_budget for project in department.projects.all())
		committed_budget = sum(project.committed_budget for project in department.projects.all())
		remaining_budget = total_budget - committed_budget

		status_counts = {
			'in_progress': department.projects.filter(status=Project.Status.IN_PROGRESS).count(),
			'on_hold': department.projects.filter(status=Project.Status.PAUSED).count(),
			'completed': department.projects.filter(status=Project.Status.COMPLETED).count(),
			'canceled': department.projects.filter(status=Project.Status.CANCELLED).count(),
		}

		dashboard_data = {
			"active_projects": {
				"number": total_projects,
				"percentage_change": "+0%"  # Placeholder for percentage change logic
			},
			"total_budget": {
				"amount": f"{total_budget} MAD",
				"percentage_change": "+0%"  # Placeholder for percentage change logic
			},
			"committed_budget": {
				"amount": f"{committed_budget} MAD",
				"percentage_change": "+0%"  # Placeholder for percentage change logic
			},
			"remaining_budget": {
				"amount": f"{remaining_budget} MAD",
				"percentage_change": "+0%"  # Placeholder for percentage change logic
			},
			"projects_by_status": status_counts,
		}
		
		return Response(dashboard_data, status=status.HTTP_200_OK)


class ListManagementUsersView(viewsets.ViewSet):

	def list(self, request):
		user = request.user
		if not user.is_director():
			return Response(
				NO_ACCESS_TO_RESOURCE,
				status=status.HTTP_403_FORBIDDEN
			)
		users = User.objects.all().order_by("id")
		role = request.query_params.get("role")
		if role:
			users = users.filter(role=role)

		paginator = get_paginator_with_requested_size(request)
		users = paginator.paginate_queryset(users, request)
		serializer = UserSerializer(users, many=True)
		return paginator.get_paginated_response(serializer.data)

	def create(self, request):
		user = request.user
		if not user.is_director():
			return Response(
				NOT_ALLOWED_TO,
				status=status.HTTP_403_FORBIDDEN
			)

		data = request.data.copy()
		password = data.pop("password", None)

		serializer = UserSerializer(data=data)
		if serializer.is_valid():
			new_user = serializer.save()
			if password:
				new_user.set_password(password)
			else:
				new_user.set_unusable_password()
			new_user.save(update_fields=["password"])
			return Response(UserSerializer(new_user).data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CreateManagementUserView(viewsets.ViewSet):

	def create(self, request):
		user = request.user
		if not user.is_director():
			return Response(
				NOT_ALLOWED_TO,
				status=status.HTTP_403_FORBIDDEN
			)

		data = request.data.copy()
		password = data.pop("password", None)

		serializer = UserSerializer(data=data)
		if serializer.is_valid():
			new_user = serializer.save()
			if password:
				new_user.set_password(password)
			else:
				new_user.set_unusable_password()
			new_user.save(update_fields=["password"])
			return Response(UserSerializer(new_user).data, status=status.HTTP_201_CREATED)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ManagementUserDetailView(viewsets.ViewSet):

	def _get_user(self, pk):
		try:
			return User.objects.get(pk=pk)
		except User.DoesNotExist:
			return None

	def retrieve(self, request, pk=None):
		user = request.user
		if not user.is_director():
			return Response(
				NO_ACCESS_TO_RESOURCE,
				status=status.HTTP_403_FORBIDDEN
			)
		target = self._get_user(pk)
		if not target:
			return Response({"details": "User not found."}, status=status.HTTP_404_NOT_FOUND)
		return Response(UserSerializer(target).data, status=status.HTTP_200_OK)

	def update(self, request, pk=None):
		user = request.user
		if not user.is_director():
			return Response(
				NOT_ALLOWED_TO,
				status=status.HTTP_403_FORBIDDEN
			)
		target = self._get_user(pk)
		if not target:
			return Response({"details": "User not found."}, status=status.HTTP_404_NOT_FOUND)

		data = request.data.copy()
		password = data.pop("password", None)
		serializer = UserSerializer(target, data=data, partial=True)
		if serializer.is_valid():
			updated = serializer.save()
			if password:
				updated.set_password(password)
				updated.save(update_fields=["password"])
			return Response(UserSerializer(updated).data, status=status.HTTP_200_OK)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	def destroy(self, request, pk=None):
		user = request.user
		if not user.is_director():
			return Response(
				NOT_ALLOWED_TO,
				status=status.HTTP_403_FORBIDDEN
			)
		target = self._get_user(pk)
		if not target:
			return Response({"details": "User not found."}, status=status.HTTP_404_NOT_FOUND)
		target.delete()
		return Response({"details": "User deleted."}, status=status.HTTP_204_NO_CONTENT)


class ListClientsView(viewsets.ViewSet):

	def list(self, request):
		user = request.user
		if not can_view_master_data(user):
			return Response(
				NO_ACCESS_TO_RESOURCE,
				status=status.HTTP_403_FORBIDDEN
			)
		clients = Client.objects.all()
		q = request.query_params.get("q")
		if q:
			clients = clients.filter(
				Q(name__icontains=q) | Q(registration_number__icontains=q)
			)

		paginator = get_paginator_with_requested_size(request)
		page = paginator.paginate_queryset(clients, request)
		serialized = [serialize_client_with_metrics(client) for client in page]
		return paginator.get_paginated_response(serialized)


class CreateClientView(viewsets.ViewSet):

	def create(self, request):
		user = request.user
		if not has_permission(user):
			return Response(
				NOT_ALLOWED_TO,
				status=status.HTTP_403_FORBIDDEN
			)
		serializer = ClientSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			return Response(
				{"details": "Client created."},
				status=status.HTTP_201_CREATED
			)
		return Response(
			serializer.errors,
			status=status.HTTP_400_BAD_REQUEST
		)


class GetClientView(viewsets.ViewSet):

	def retrieve(self, request, pk=None):
		user = request.user
		if not can_view_master_data(user):
			return Response(
				NO_ACCESS_TO_RESOURCE,
				status=status.HTTP_403_FORBIDDEN
			)
		client = getClient(pk)
		if not client:
			return Response(
				CLIENT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		return Response(
			serialize_client_with_metrics(client),
			status=status.HTTP_200_OK
		)

	def update(self, request, pk=None):
		user = request.user
		if not has_permission(user):
			return Response(
				NOT_ALLOWED_TO,
				status=status.HTTP_403_FORBIDDEN
			)
		client = getClient(pk)
		if not client:
			return Response(
				CLIENT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		serializer = ClientSerializer(client, data=request.data, partial=True)
		if serializer.is_valid():
			serializer.save()
			return Response(
				{"details": "Client details updated."},
				status=status.HTTP_200_OK
			)
		return Response(
			serializer.errors,
			status=status.HTTP_400_BAD_REQUEST
		)

	def destroy(self, request, pk=None):
		user = request.user
		if not has_permission(user):
			return Response(
				NOT_ALLOWED_TO,
				status=status.HTTP_403_FORBIDDEN
			)
		client = getClient(pk)
		if not client:
			return Response(
				CLIENT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		client.delete()
		return Response(
			{"details": "Client deleted."},
			status=status.HTTP_204_NO_CONTENT
		)


class GetClientTotalsView(viewsets.ViewSet):

	def retrieve(self, request, pk=None):
		user = request.user
		if not can_view_master_data(user):
			return Response(
				NO_ACCESS_TO_RESOURCE,
				status=status.HTTP_403_FORBIDDEN
			)
		client = getClient(pk)
		if not client:
			return Response(
				CLIENT_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		return Response(
			get_client_totals_payload(client),
			status=status.HTTP_200_OK
		)


class ListSuppliersView(viewsets.ViewSet):

	def list(self, request):
		user = request.user
		if not can_view_master_data(user):
			return Response(
				NO_ACCESS_TO_RESOURCE,
				status=status.HTTP_403_FORBIDDEN
			)
		suppliers = Supplier.objects.all()
		q = request.query_params.get("q")
		if q:
			suppliers = suppliers.filter(
				Q(name__icontains=q) | Q(registration_number__icontains=q)
			)

		paginator = get_paginator_with_requested_size(request)
		page = paginator.paginate_queryset(suppliers, request)
		serialized = [serialize_supplier_with_metrics(supplier) for supplier in page]
		return paginator.get_paginated_response(serialized)


class CreateSupplierView(viewsets.ViewSet):

	def create(self, request):
		user = request.user
		if not has_permission(user):
			return Response(
				NOT_ALLOWED_TO,
				status=status.HTTP_403_FORBIDDEN
			)
		serializer = SupplierSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save()
			return Response(
				{"details": "Supplier created."},
				status=status.HTTP_201_CREATED
			)
		return Response(
			serializer.errors,
			status=status.HTTP_400_BAD_REQUEST
		)


class GetSupplierView(viewsets.ViewSet):

	def retrieve(self, request, pk=None):
		user = request.user
		if not can_view_master_data(user):
			return Response(
				NO_ACCESS_TO_RESOURCE,
				status=status.HTTP_403_FORBIDDEN
			)
		supplier = getSupplier(pk)
		if not supplier:
			return Response(
				SUPPLIER_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		return Response(
			serialize_supplier_with_metrics(supplier),
			status=status.HTTP_200_OK
		)

	def update(self, request, pk=None):
		user = request.user
		if not has_permission(user):
			return Response(
				NOT_ALLOWED_TO,
				status=status.HTTP_403_FORBIDDEN
			)
		supplier = getSupplier(pk)
		if not supplier:
			return Response(
				SUPPLIER_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		serializer = SupplierSerializer(supplier, data=request.data, partial=True)
		if serializer.is_valid():
			serializer.save()
			return Response(
				{"details": "Supplier details updated."},
				status=status.HTTP_200_OK
			)
		return Response(
			serializer.errors,
			status=status.HTTP_400_BAD_REQUEST
		)

	def destroy(self, request, pk=None):
		user = request.user
		if not has_permission(user):
			return Response(
				NOT_ALLOWED_TO,
				status=status.HTTP_403_FORBIDDEN
			)
		supplier = getSupplier(pk)
		if not supplier:
			return Response(
				SUPPLIER_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		supplier.delete()
		return Response(
			{"details": "Supplier deleted."},
			status=status.HTTP_204_NO_CONTENT
		)


class GetSupplierTotalsView(viewsets.ViewSet):

	def retrieve(self, request, pk=None):
		user = request.user
		if not can_view_master_data(user):
			return Response(
				NO_ACCESS_TO_RESOURCE,
				status=status.HTTP_403_FORBIDDEN
			)
		supplier = getSupplier(pk)
		if not supplier:
			return Response(
				SUPPLIER_NOT_FOUND,
				status=status.HTTP_404_NOT_FOUND
			)
		return Response(
			get_supplier_totals_payload(supplier),
			status=status.HTTP_200_OK
		)