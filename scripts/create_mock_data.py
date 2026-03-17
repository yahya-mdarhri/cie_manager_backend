import random
from faker import Faker
from django.contrib.auth import get_user_model
from management.models import Department, Project, Expense, PaymentReceived

fake = Faker()
User = get_user_model()


def format_currency(value: int) -> int:
    return int(value)


def run():
    # --- Clear old mock data (optional) ---
    Expense.objects.all().delete()
    PaymentReceived.objects.all().delete()
    Project.objects.all().delete()
    Department.objects.all().delete()
    User.objects.exclude(is_superuser=True).delete()

    # --- Create Directors ---
    directors = []
    for _ in range(2):
        director = User.objects.create_user(
            username=fake.unique.user_name(),
            email=fake.unique.email(),
            password="password123",
            role=User.Role.DIRECTOR,
            department=None,
        )
        directors.append(director)
    print("[DONE] Directors created")

    # --- Create Departments + Managers (fixed whitelist) ---
    departments = []
    managers = []
    whitelist = [
        "CIE Direct",
        "Tech Center",
        "TTO",
        "Clinique Industrielle",
    ]
    for dept_name in whitelist:
        dept = Department.objects.create(
            name=dept_name,
            description=fake.text(max_nb_chars=150),
        )
        departments.append(dept)

        manager = User.objects.create_user(
            username=fake.unique.user_name(),
            email=fake.unique.email(),
            password="password123",
            role=User.Role.DEPARTMENT_MANAGER,
            department=dept,
        )
        managers.append(manager)

    print("[DONE] Departments + Managers created")


    # --- Create Projects (deterministic per department) ---
    projects = []
    predefined: dict[str, list[dict]] = {
        "CIE Direct": [
            {
                "code": "CIE-PO-0001",
                "name": "Programme d'Innovation Interne",
                "nature": "Purchase Order",
                "client": "CIE",
                "budget": 750000,
            },
            {
                "code": "CIE-AGR-0002",
                "name": "Partenariat Open Innovation",
                "nature": "Agreement",
                "client": "Consortium UIR",
                "budget": 420000,
            },
        ],
        "Tech Center": [
            {
                "code": "TC-PO-0007",
                "name": "Retrofitting de tondeuse à greens",
                "nature": "Purchase Order",
                "client": "Client A",
                "budget": 13680000,
            },
            {
                "code": "TC-CTR-0013",
                "name": "Ligne de prototypage rapide",
                "nature": "Contract",
                "client": "Client B",
                "budget": 6840000,
            },
        ],
        "TTO": [
            {
                "code": "TTO-AGR-0003",
                "name": "innov'acteurs",
                "nature": "Agreement",
                "client": "Client C",
                "budget": 439500,
            },
            {
                "code": "TTO-GR-0004",
                "name": "Transfert techno santé",
                "nature": "Grant",
                "client": "Fondation Santé",
                "budget": 820000,
            },
        ],
        "Clinique Industrielle": [
            {
                "code": "CI-PO-0005",
                "name": "Clinique de maintenance prédictive",
                "nature": "Purchase Order",
                "client": "Client D",
                "budget": 1250000,
            },
            {
                "code": "CI-CTR-0006",
                "name": "Optimisation énergétique",
                "nature": "Contract",
                "client": "Client E",
                "budget": 980000,
            },
        ],
    }

    for dept in departments:
        items = predefined.get(dept.name)
        if not items:
            items = [
                {
                    "code": fake.unique.bothify("GEN-####"),
                    "name": fake.catch_phrase(),
                    "nature": random.choice([c[0] for c in Project.ProjectNature.choices]),
                    "client": fake.company(),
                    "budget": fake.random_int(min=100000, max=8000000),
                }
                for _ in range(2)
            ]
        for item in items:
            total_budget = int(item["budget"])
            committed_budget = fake.random_int(min=0, max=total_budget)
            proj = Project.objects.create(
                project_code=item["code"],
                project_name=item["name"],
                coordinator=fake.name(),
                project_nature=item["nature"],
                department=dept,
                end_date=fake.date_between(start_date="+30d", end_date="+365d"),
                total_budget=format_currency(total_budget),
                committed_budget=format_currency(committed_budget),
                agreement_number=fake.bothify("AGR-####"),
                client_name=item["client"],
                description=fake.text(max_nb_chars=150),
                objective=fake.text(max_nb_chars=80),
                partners=fake.company(),
                risks=fake.text(max_nb_chars=60),
                signature_date=fake.date_between(start_date="-60d", end_date="-30d"),
                needs_expression_date=fake.date_between(start_date="-120d", end_date="-90d"),
                client_po_date=fake.date_between(start_date="-80d", end_date="-60d"),
                cg_validation_date=fake.date_between(start_date="-55d", end_date="-40d"),
                da_creation_date=fake.date_between(start_date="-39d", end_date="-35d"),
                purchase_request_date=fake.date_between(start_date="-34d", end_date="-30d"),
            )
            projects.append(proj)
    print("[DONE] Projects created")

    # --- Create Expenses + Payments ---
    for proj in projects:
        for _ in range(random.randint(3, 5)):
            exp = Expense.objects.create(
                project=proj,
                amount=fake.pydecimal(left_digits=5, right_digits=2, positive=True),
                expense_date=fake.date_between(start_date="-120d", end_date="today"),
                category=random.choice([c[0] for c in Expense.Category.choices]),
                supplier=fake.company(),
                invoice_reference=fake.bothify("INV-####"),
                description=fake.text(max_nb_chars=120),
                document_path=fake.file_path(extension="pdf"),
                payment_date=fake.date_between(start_date="-120d", end_date="today"),
            )
            # created

        for _ in range(random.randint(1, 3)):
            pay = PaymentReceived.objects.create(
                project=proj,
                amount=fake.pydecimal(left_digits=5, right_digits=2, positive=True),
                payment_received_date=fake.date_between(start_date="-120d", end_date="today"),
                payment_type=random.choice([c[0] for c in PaymentReceived.PaymentType.choices]),
                payment_reference=fake.bothify("PAY-####"),
                description=fake.text(max_nb_chars=100),
            )
            # created

    print("[DONE] Expenses + Payments created")
    print("[DONE] Mock data generation complete")
