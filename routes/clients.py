from decimal import Decimal, InvalidOperation
import re

from flask import Blueprint, flash, redirect, render_template, request, url_for

import repository

bp = Blueprint("clients", __name__, url_prefix="/clients")

ACCOUNT_INDEX_RE = re.compile(r"^account_type_(\d+)$")
LIABILITY_INDEX_RE = re.compile(r"^liability_type_(\d+)$")


def _money_to_cents(raw_value, allow_blank=False):
    cleaned = (raw_value or "").strip()
    if not cleaned:
        if allow_blank:
            return None
        raise ValueError("This amount is required.")

    try:
        return int(Decimal(cleaned) * 100)
    except InvalidOperation as exc:
        raise ValueError("Enter a valid amount.") from exc


def _decimal_or_none(raw_value):
    cleaned = (raw_value or "").strip()
    if not cleaned:
        return None

    try:
        return Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError("Enter a valid rate.") from exc


def _blank_form_data():
    return {
        "household_name": "",
        "marital_status": "single",
        "monthly_salary": "",
        "monthly_expense_budget": "",
        "insurance_deductibles": "",
        "reserve_target_override": "",
        "trust_property_address": "",
        "persons": {
            "client_1": {"first_name": "", "last_name": "", "date_of_birth": "", "ssn_last_four": ""},
            "client_2": {"first_name": "", "last_name": "", "date_of_birth": "", "ssn_last_four": ""},
        },
        "accounts": [
            {
                "id": "",
                "category": "retirement",
                "owner_role": "client_1",
                "account_type": "",
                "account_number_last_four": "",
                "institution": "",
                "is_investment_account": True,
            }
        ],
        "liabilities": [
            {"id": "", "liability_type": "", "description": "", "interest_rate": ""}
        ],
    }


def _profile_to_form_data(profile):
    form_data = {
        "household_name": profile.get("household_name", ""),
        "marital_status": profile.get("marital_status", "single"),
        "monthly_salary": f"{(profile.get('monthly_salary_cents') or 0) / 100:.2f}",
        "monthly_expense_budget": f"{(profile.get('monthly_expense_budget_cents') or 0) / 100:.2f}",
        "insurance_deductibles": f"{(profile.get('insurance_deductibles_cents') or 0) / 100:.2f}",
        "reserve_target_override": "",
        "trust_property_address": profile.get("trust", {}).get("property_address", "") if profile.get("trust") else "",
        "persons": {
            "client_1": {"first_name": "", "last_name": "", "date_of_birth": "", "ssn_last_four": ""},
            "client_2": {"first_name": "", "last_name": "", "date_of_birth": "", "ssn_last_four": ""},
        },
        "accounts": [],
        "liabilities": [],
    }

    if profile.get("reserve_target_override_cents") is not None:
        form_data["reserve_target_override"] = f"{profile['reserve_target_override_cents'] / 100:.2f}"

    for person in profile.get("persons", []):
        form_data["persons"][person["person_role"]] = {
            "first_name": person.get("first_name", ""),
            "last_name": person.get("last_name", ""),
            "date_of_birth": person.get("date_of_birth", ""),
            "ssn_last_four": person.get("ssn_last_four", ""),
        }

    person_role_by_id = {person["id"]: person["person_role"] for person in profile.get("persons", [])}
    for account in profile.get("accounts", []):
        form_data["accounts"].append(
            {
                "id": account["id"],
                "category": account.get("category", "retirement"),
                "owner_role": person_role_by_id.get(account.get("person_id"), "joint"),
                "account_type": account.get("account_type", ""),
                "account_number_last_four": account.get("account_number_last_four", "") or "",
                "institution": account.get("institution", "") or "",
                "is_investment_account": bool(account.get("is_investment_account")),
            }
        )

    for liability in profile.get("liabilities", []):
        form_data["liabilities"].append(
            {
                "id": liability["id"],
                "liability_type": liability.get("liability_type", ""),
                "description": liability.get("description", "") or "",
                "interest_rate": str(liability.get("interest_rate") or ""),
            }
        )

    if not form_data["accounts"]:
        form_data["accounts"] = _blank_form_data()["accounts"]
    if not form_data["liabilities"]:
        form_data["liabilities"] = _blank_form_data()["liabilities"]

    return form_data


def _parse_client_form(form):
    errors = []
    marital_status = form.get("marital_status", "single")

    def required_text(field_name, label):
        value = (form.get(field_name) or "").strip()
        if not value:
            errors.append(f"{label} is required.")
        return value

    def parse_person(role, label):
        return {
            "first_name": required_text(f"{role}_first_name", f"{label} first name"),
            "last_name": required_text(f"{role}_last_name", f"{label} last name"),
            "date_of_birth": required_text(f"{role}_date_of_birth", f"{label} date of birth"),
            "ssn_last_four": required_text(f"{role}_ssn_last_four", f"{label} SSN last four"),
        }

    try:
        monthly_salary_cents = _money_to_cents(form.get("monthly_salary"))
    except ValueError as exc:
        errors.append(f"Monthly salary: {exc}")
        monthly_salary_cents = 0

    try:
        monthly_expense_budget_cents = _money_to_cents(form.get("monthly_expense_budget"))
    except ValueError as exc:
        errors.append(f"Monthly expense budget: {exc}")
        monthly_expense_budget_cents = 0

    try:
        insurance_deductibles_cents = _money_to_cents(form.get("insurance_deductibles"))
    except ValueError as exc:
        errors.append(f"Insurance deductibles: {exc}")
        insurance_deductibles_cents = 0

    try:
        reserve_target_override_cents = _money_to_cents(
            form.get("reserve_target_override"), allow_blank=True
        )
    except ValueError as exc:
        errors.append(f"Reserve target override: {exc}")
        reserve_target_override_cents = None

    persons = {"client_1": parse_person("client_1", "Client 1")}
    if marital_status == "married":
        persons["client_2"] = parse_person("client_2", "Client 2")

    accounts = []
    account_indices = sorted(
        int(match.group(1))
        for key in form.keys()
        for match in [ACCOUNT_INDEX_RE.match(key)]
        if match
    )
    for index in account_indices:
        account_type = (form.get(f"account_type_{index}") or "").strip()
        institution = (form.get(f"account_institution_{index}") or "").strip()
        if not account_type and not institution:
            continue

        category = form.get(f"account_category_{index}", "retirement")
        owner_role = form.get(f"account_owner_{index}", "client_1")
        if category == "retirement" and owner_role == "joint":
            errors.append(f"Account row {index + 1}: retirement accounts must belong to Client 1 or Client 2.")

        accounts.append(
            {
                "id": int(form.get(f"account_id_{index}")) if form.get(f"account_id_{index}") else None,
                "category": category,
                "owner_role": owner_role,
                "account_type": account_type,
                "account_number_last_four": (form.get(f"account_last_four_{index}") or "").strip(),
                "institution": institution,
                "is_investment_account": form.get(f"account_is_investment_{index}") == "on",
            }
        )

    if not accounts:
        errors.append("At least one account is required.")

    liabilities = []
    liability_indices = sorted(
        int(match.group(1))
        for key in form.keys()
        for match in [LIABILITY_INDEX_RE.match(key)]
        if match
    )
    for index in liability_indices:
        liability_type = (form.get(f"liability_type_{index}") or "").strip()
        description = (form.get(f"liability_description_{index}") or "").strip()
        if not liability_type and not description:
            continue

        try:
            interest_rate = _decimal_or_none(form.get(f"liability_interest_rate_{index}"))
        except ValueError as exc:
            errors.append(f"Liability row {index + 1}: {exc}")
            interest_rate = None

        liabilities.append(
            {
                "id": int(form.get(f"liability_id_{index}")) if form.get(f"liability_id_{index}") else None,
                "liability_type": liability_type or "Liability",
                "description": description,
                "interest_rate": float(interest_rate) if interest_rate is not None else None,
            }
        )

    payload = {
        "household_name": required_text("household_name", "Household name"),
        "marital_status": marital_status,
        "monthly_salary_cents": monthly_salary_cents,
        "monthly_expense_budget_cents": monthly_expense_budget_cents,
        "insurance_deductibles_cents": insurance_deductibles_cents,
        "reserve_target_override_cents": reserve_target_override_cents,
        "trust_property_address": (form.get("trust_property_address") or "").strip(),
        "persons": persons,
        "accounts": accounts,
        "liabilities": liabilities,
    }

    form_data = {
        "household_name": form.get("household_name", ""),
        "marital_status": marital_status,
        "monthly_salary": form.get("monthly_salary", ""),
        "monthly_expense_budget": form.get("monthly_expense_budget", ""),
        "insurance_deductibles": form.get("insurance_deductibles", ""),
        "reserve_target_override": form.get("reserve_target_override", ""),
        "trust_property_address": form.get("trust_property_address", ""),
        "persons": {
            "client_1": {
                "first_name": form.get("client_1_first_name", ""),
                "last_name": form.get("client_1_last_name", ""),
                "date_of_birth": form.get("client_1_date_of_birth", ""),
                "ssn_last_four": form.get("client_1_ssn_last_four", ""),
            },
            "client_2": {
                "first_name": form.get("client_2_first_name", ""),
                "last_name": form.get("client_2_last_name", ""),
                "date_of_birth": form.get("client_2_date_of_birth", ""),
                "ssn_last_four": form.get("client_2_ssn_last_four", ""),
            },
        },
        "accounts": accounts or _blank_form_data()["accounts"],
        "liabilities": liabilities or _blank_form_data()["liabilities"],
    }

    return payload, form_data, errors


@bp.route("/")
def list_clients():
    clients = repository.get_clients_with_last_report()
    return render_template("client_list.html", clients=clients)


@bp.route("/new", methods=["GET", "POST"])
def new_client():
    form_data = _blank_form_data()
    if request.method == "POST":
        payload, form_data, errors = _parse_client_form(request.form)
        if not errors:
            client_id = repository.create_client_profile(payload)
            flash("Client profile created.", "success")
            return redirect(url_for("clients.client_detail", client_id=client_id))
        for error in errors:
            flash(error, "error")

    return render_template(
        "client_form.html",
        mode="create",
        client=None,
        form_data=form_data,
    )


@bp.route("/<int:client_id>")
def client_detail(client_id):
    client = repository.get_client_detail(client_id)
    if not client:
        return "Client not found", 404
    return render_template("client_detail.html", client=client)


@bp.route("/<int:client_id>/edit", methods=["GET", "POST"])
def edit_client(client_id):
    client = repository.get_client_detail(client_id)
    if not client:
        return "Client not found", 404

    form_data = _profile_to_form_data(client)
    if request.method == "POST":
        payload, form_data, errors = _parse_client_form(request.form)
        if not errors:
            repository.update_client_profile(client_id, payload)
            flash("Client profile updated.", "success")
            return redirect(url_for("clients.client_detail", client_id=client_id))
        for error in errors:
            flash(error, "error")

    return render_template(
        "client_form.html",
        mode="edit",
        client=client,
        form_data=form_data,
    )
