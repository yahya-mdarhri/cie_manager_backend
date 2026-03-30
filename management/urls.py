from django.urls import path
from .views import ListDepartmentView, CreateDepartmentView, GetDepartmentView, SetDepartmentManagerView
from .views import ListProjectsView, CreateProjectView, GetProjectView
from .views import ListProjectExpensesView, CreateProjectExpenseView, GetProjectExpenseView
from .views import ListProjectPaymentsReceivedView, CreateProjectPaymentReceivedView, GetProjectPaymentReceivedView
from .views import ListActionLogsView, GetActionLogView
from .views import ListProjectStepsView, CreateProjectStepView, GetProjectStepView, ExecuteProjectStepView
from .views import ListAllProjectView, ListAllExpensesView, ListAllPaymentsReceivedView
from .views import DirectorDashboardView, DepartmentDashboardView
from .views import ListClientsView, CreateClientView, GetClientView, GetClientTotalsView
from .views import ListSuppliersView, CreateSupplierView, GetSupplierView, GetSupplierTotalsView


urlpatterns = [
	path(
		"departments/",
		ListDepartmentView.as_view({'get': 'list'}),
		name="departments"
	),
	path(
		"departments/create/",
		CreateDepartmentView.as_view({'post': 'create'}),
		name="create-department"
	),
	path(
		"departments/<int:pk>/",
		GetDepartmentView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}),
		name="department-detail"
	),
	path(
		"departments/<int:dep>/set-manager/",
		SetDepartmentManagerView.as_view({'put': 'update'}),
		name="set-department-manager"
	),
	path(
		"departments/<int:pk>/projects/",
		ListProjectsView.as_view({'get': 'list'}),
		name="department-projects"
	),
	path(
		"departments/<int:dep>/projects/<int:proj>/",
		GetProjectView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}),
		name="department-project-details"
	),
	path(
		"departments/<int:dep>/projects/create/",
		CreateProjectView.as_view({'post': 'create'}),
		name="create-department-project"
	),

	path(
		"departments/<int:dep>/projects/<int:proj>/expenses/",
		ListProjectExpensesView.as_view({'get': 'list'}),
		name="project-expenses"
	),
	path(
		"departments/<int:dep>/projects/<int:proj>/expenses/<int:exp>/",
		GetProjectExpenseView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}),
		name="project-expense-details"
	),
	path
	(
		"departments/<int:dep>/projects/<int:proj>/expenses/create/",
		CreateProjectExpenseView.as_view({'post': 'create'}),
		name="create-project-expense"
	),

	path(
		"departments/<int:dep>/projects/<int:proj>/payments/",
		ListProjectPaymentsReceivedView.as_view({'get': 'list'}),
		name="project-payments"
	),
	path(
		"departments/<int:dep>/projects/<int:proj>/payments/<int:pay>/",
		GetProjectPaymentReceivedView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}),
		name="project-payment-details"
	),
	path(
		"departments/<int:dep>/projects/<int:proj>/payments/create/",
		CreateProjectPaymentReceivedView.as_view({'post': 'create'}),
		name="create-project-payment"
	),
	path(
		"action-logs/",
		ListActionLogsView.as_view({'get': 'list'}),
		name="action-logs"
	),
	path(
		"action-logs/<int:pk>/",
		GetActionLogView.as_view({'get': 'retrieve'}),
		name="action-log-detail"
	),

	path(
		"departments/<int:dep>/projects/<int:proj>/steps/",
		ListProjectStepsView.as_view({'get': 'list'}),
		name="project-steps"
	),
	path(
		"departments/<int:dep>/projects/<int:proj>/steps/create/",
		CreateProjectStepView.as_view({'post': 'create'}),
		name="create-project-step"
	),
	path(
		"departments/<int:dep>/projects/<int:proj>/steps/<int:step>/",
		GetProjectStepView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}),
		name="project-step-details"
	),
	path(
		"departments/<int:dep>/projects/<int:proj>/steps/<int:step>/execute/",
		ExecuteProjectStepView.as_view({'put': 'execute'}),
		name="update-project-step-status"
	),
	path(
		"all/projects/",
		ListAllProjectView.as_view({'get': 'list'}),
		name="all-projects"
	),

	path("all/expenses/",
		ListAllExpensesView.as_view({'get': 'list'}),
		name="all-expenses"
	),
	path("all/payments/",
		ListAllPaymentsReceivedView.as_view({'get': 'list'}),
		name="all-payments"
	),

	path("all/statistics/",
		DirectorDashboardView.as_view({'get': 'retrieve'}),
		name="all-statistics"
	),
	path("departments/<int:dep>/statistics/",
		DepartmentDashboardView.as_view({'get': 'retrieve'}),
		name="department-statistics"
	),
	path(
		"clients/",
		ListClientsView.as_view({'get': 'list'}),
		name="clients"
	),
	path(
		"clients/create/",
		CreateClientView.as_view({'post': 'create'}),
		name="create-client"
	),
	path(
		"clients/<int:pk>/",
		GetClientView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}),
		name="client-detail"
	),
	path(
		"clients/<int:pk>/totals/",
		GetClientTotalsView.as_view({'get': 'retrieve'}),
		name="client-totals"
	),
	path(
		"suppliers/",
		ListSuppliersView.as_view({'get': 'list'}),
		name="suppliers"
	),
	path(
		"suppliers/create/",
		CreateSupplierView.as_view({'post': 'create'}),
		name="create-supplier"
	),
	path(
		"suppliers/<int:pk>/",
		GetSupplierView.as_view({'get': 'retrieve', 'put': 'update', 'delete': 'destroy'}),
		name="supplier-detail"
	),
	path(
		"suppliers/<int:pk>/totals/",
		GetSupplierTotalsView.as_view({'get': 'retrieve'}),
		name="supplier-totals"
	),
]
