import json
from rest_framework import status, viewsets
from rest_framework.response import Response
from django.contrib.auth import get_user_model

from accounts.permissions import has_permission
from management.models import Department, Project, Expense, PaymentReceived, ActionLogs, ProjectSteps
from management.pagination import CustomPagination
from management.serializers import DepartmentSerializer, ProjectSerializer, ExpenseSerializer, PaymentReceivedSerializer, ActionLogsSerializer, ProjectStepsSerializer

User = get_user_model()

NO_ACCESS_TO_RESOURCE = {"details": "You do not have permission to view this resource."}
DEPARTMENT_NOT_FOUND  = {"details": "Department not found."}
PROJECT_NOT_FOUND     = {"details": "Project not found."}
EXPENSE_NOT_FOUND     = {"details": "Expense not found."}
NOT_ALLOWED_TO = {"details": "You do not have permission to make this action."}

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
		#Check if the provided details are valid, if yes save them, otherwise no
		serializer = DepartmentSerializer(department, data=request.data, partial=True)
		if serializer.is_valid():
			serializer.save()
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
		# Create the project
		serializer = ProjectSerializer(data=request.data)
		if serializer.is_valid():
			serializer.save(department=department)
			project = serializer.instance
			if "jalons" in request.data:
				steps_data = request.data["jalons"]
				step_json = json.loads(steps_data)
				for step in step_json["jalons"]:
					step_serializer = ProjectStepsSerializer(data=step)
					if step_serializer.is_valid():
						step_serializer.save(project=project)
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
		serializer = ExpenseSerializer(data=request.data)
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
		serializer = PaymentReceivedSerializer(data=request.data)
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
			expenses = Expense.objects.all()
			expenses = paginator.paginate_queryset(expenses, request)
			serializer = ExpenseSerializer(expenses, many=True)
			return paginator.get_paginated_response(serializer.data)
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
			payments_received = PaymentReceived.objects.all()
			payments_received = paginator.paginate_queryset(payments_received, request)
			serializer = PaymentReceivedSerializer(payments_received, many=True)
			return paginator.get_paginated_response(serializer.data)
		return Response(
			NO_ACCESS_TO_RESOURCE,
			status=status.HTTP_403_FORBIDDEN
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