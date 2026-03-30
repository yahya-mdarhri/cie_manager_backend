from datetime import datetime, timezone
from rest_framework import serializers
from .models import *

class DepartmentSerializer(serializers.ModelSerializer):
	class Meta:
		model = Department
		fields = [
			"id", "name", "description", "created_at", "updated_at"
		]
		read_only_fields = ["id", "created_at", "updated_at"]

class ExpenseSerializer(serializers.ModelSerializer):
	class Meta:
		model = Expense
		fields = '__all__'
		extra_kwargs = {
			"project": {"required": True},
			"amount": {"required": True},
			"expense_date": {"required": True},
			"category": {"required": True},

			"id": {"read_only": True},
			"created_at": {"read_only": True},
		}

class PaymentReceivedSerializer(serializers.ModelSerializer):
	class Meta:
		model = PaymentReceived
		fields = '__all__'
		extra_kwargs = {
			"id": {"read_only": True},
			"created_at": {"read_only": True},


			"project": {"required": True},
			"amount": {"required": True},
			"payment_type": {"required": True},
			"payment_reference": {"required": True},
			"payment_received_date": {"required": True},
		}

class ProjectSerializer(serializers.ModelSerializer):
	department = DepartmentSerializer(read_only=True)
	#expenses = ExpenseSerializer(many=True, read_only=True)
	#payments_received = PaymentReceivedSerializer(many=True, read_only=True)

	class Meta:
		model = Project
		fields = '__all__'
		extra_kwargs = {
			"project_code": {"required": True},
			"project_name": {"required": True},
			"coordinator": {"required": True},
			"project_nature": {"required": True},
			"end_date": {"required": True},
			"total_budget": {"required": True},
			"client_name": {"required": True},
			"contract_documents": {"required": True},
			"needs_expression_date": {"required": True},
			"client_po_date": {"required": True},
			"description": {"required": True},
			"objective": {"required": True},

			"id": {"read_only": True},
			"committed_budget": {"read_only": True},
			"remaining_budget": {"read_only": True},
			"department": {"read_only": True},
			"created_at": {"read_only": True},
			"updated_at": {"read_only": True},
			"expenses": {"read_only": True},
			"payments_received": {"read_only": True},
		}

# validate dates and money values
	def validate(self, data):
		self.validate_dates(data)
		self.validate_money(data)
		return data


	def validate_dates(self, data):
		date_fields = [
			"end_date", "signature_date", "needs_expression_date", "client_po_date",
			"cg_validation_date", "da_creation_date", "purchase_request_date",
			"uir_po_send_date", "uir_delivery_date", "invoicing_date", "payment_received_date"
		]
		dates = {field: data.get(field) for field in date_fields if data.get(field) is not None}

		# Check if end_date is after all other dates
		end_date = dates.get("end_date")
		if end_date:
			for field, date in dates.items():
				if field != "end_date" and date and end_date < date:
					raise serializers.ValidationError(f"End date must be after {field.replace('_', ' ')}.")

		# Check chronological order of other dates
		sorted_dates = sorted(dates.items(), key=lambda x: x[1])
		for i in range(len(sorted_dates) - 1):
			if sorted_dates[i][1] > sorted_dates[i + 1][1]:
				raise serializers.ValidationError(
					f"{sorted_dates[i][0].replace('_', ' ')} must be before {sorted_dates[i + 1][0].replace('_', ' ')}."
				)

		# Check if any date is in the past
		# for field, date in dates.items():
		# 	now = datetime.now(timezone.utc).date()
		# 	if date < now:
		# 		raise serializers.ValidationError(f"{field.replace('_', ' ')} must be in the future.")

	def validate_money(self, data):
		price_fields = [
			"total_budget", "personnel_budget", "equipment_budget", "subcontracting_budget",
			"mobility_budget", "consumables_budget", "other_budget"
		]
		prices = {field: data.get(field) for field in price_fields if data.get(field) is not None}
		total_budget = prices.get("total_budget")
		if total_budget is not None:
			sum_of_budgets = sum(value for key, value in prices.items() if key != "total_budget" and value is not None)
			if sum_of_budgets > total_budget:
				raise serializers.ValidationError("Sum of category budgets cannot exceed total budget.")
		if total_budget is not None and total_budget < 0:
			raise serializers.ValidationError("Total budget must be non-negative.")
		for field, value in prices.items():
			if value is not None and value < 0:
				raise serializers.ValidationError(f"{field.replace('_', ' ')} must be non-negative.")


class ActionLogsSerializer(serializers.ModelSerializer):
	content_type = serializers.SerializerMethodField()

	def get_content_type(self, obj):
		return str(obj.content_type.model)

	class Meta:
		model = ActionLogs
		fields = "__all__"

class ProjectStepsSerializer(serializers.ModelSerializer):
	class Meta:
		model = ProjectSteps
		fields = '__all__'
		extra_kwargs = {
			"id": {"read_only": True},
			"project": {"read_only": True},
			"created_at": {"read_only": True},
			"updated_at": {"read_only": True},
			"execution_status": {"required": False},

			"step_name": {"required": True},
			"start_date": {"required": True},
			"end_date": {"required": True},
		}

	def validate(self, data):
		end = data.get('end_date')
		start = data.get('start_date')
		if start and end and start > end:
			raise serializers.ValidationError("End date must be after start date.")
		return data


class ClientSerializer(serializers.ModelSerializer):
	class Meta:
		model = Client
		fields = ["id", "name", "registration_number", "created_at", "updated_at"]
		extra_kwargs = {
			"id": {"read_only": True},
			"created_at": {"read_only": True},
			"updated_at": {"read_only": True},
			"name": {"required": True},
			"registration_number": {"required": True},
		}


class SupplierSerializer(serializers.ModelSerializer):
	class Meta:
		model = Supplier
		fields = ["id", "name", "registration_number", "created_at", "updated_at"]
		extra_kwargs = {
			"id": {"read_only": True},
			"created_at": {"read_only": True},
			"updated_at": {"read_only": True},
			"name": {"required": True},
			"registration_number": {"required": True},
		}