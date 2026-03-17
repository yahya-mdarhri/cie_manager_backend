# -*- coding: utf-8 -*-
from django.contrib import admin

from .models import *


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'created_at', 'updated_at')
    list_filter = ('created_at', 'updated_at')
    search_fields = ('name',)
    date_hierarchy = 'created_at'


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'project_code',
        'project_name',
        'coordinator',
        'project_nature',
        'department',
        'end_date',
        'total_budget',
        'committed_budget',
        'remaining_budget',
        'status',
        'personnel_budget',
        'equipment_budget',
        'subcontracting_budget',
        'mobility_budget',
        'consumables_budget',
        'other_budget',
        'agreement_number',
        'client_name',
        'contract_documents',
        'signature_date',
        'needs_expression_date',
        'client_po_date',
        'cg_validation_date',
        'da_creation_date',
        'purchase_request_date',
        'uir_po_send_date',
        'uir_delivery_date',
        'invoicing_date',
        'payment_received_date',
        'description',
        'objective',
        'partners',
        'risks',
        'created_at',
        'updated_at',
    )
    list_filter = (
        'department',
        'end_date',
        'signature_date',
        'needs_expression_date',
        'client_po_date',
        'cg_validation_date',
        'da_creation_date',
        'purchase_request_date',
        'uir_po_send_date',
        'uir_delivery_date',
        'invoicing_date',
        'payment_received_date',
        'created_at',
        'updated_at',
    )
    date_hierarchy = 'created_at'


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'project',
        'amount',
        'expense_date',
        'category',
        'supplier',
        'invoice_reference',
        'description',
        'document_path',
        'payment_date',
        'created_at',
    )
    list_filter = ('project', 'expense_date', 'payment_date', 'created_at')
    date_hierarchy = 'created_at'


@admin.register(PaymentReceived)
class PaymentReceivedAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'project',
        'amount',
        'payment_received_date',
        'payment_type',
        'payment_reference',
        'description',
        'created_at',
    )
    list_filter = ('project', 'payment_received_date', 'created_at')
    date_hierarchy = 'created_at'


from django.contrib import admin
from .models import ActionLogs

@admin.register(ActionLogs)
class ActionLogsAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "action",
        "model_name",
        "object_id",
        "timestamp",
    )
    list_filter = ("action", "content_type", "timestamp")
    search_fields = ("user__username", "object_id", "user_agent", "ip_address")
    readonly_fields = ("user", "content_type", "object_id", "action", "changes", "ip_address", "user_agent", "timestamp")

    def model_name(self, obj):
        return obj.content_type.model_class().__name__ if obj.content_type else "-"
    model_name.short_description = "Model"

# ProjectSteps
@admin.register(ProjectSteps)
class ProjectStepsAdmin(admin.ModelAdmin):
		list_display = (
				'id',
				'project',
				'name',
				'description',
				'start_date',
				'end_date',
				'execution_status',
				'execution_comments',
				'execution_proof',
				'created_at',
		)
		list_filter = ('project', 'start_date', 'end_date', 'execution_status', 'created_at')
		date_hierarchy = 'created_at'