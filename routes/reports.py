from decimal import Decimal, InvalidOperation
from datetime import datetime
from flask import Blueprint, flash, redirect, render_template, request, url_for

import repository
from calculations import calculate_reserve_target, calculate_sacs_excess

bp = Blueprint("reports", __name__, url_prefix="/reports")


def _money_to_cents(raw_value, field_label):
    cleaned = (raw_value or "").strip()
    if not cleaned:
        raise ValueError(f"{field_label} is required.")

    try:
        return int(Decimal(cleaned) * 100)
    except InvalidOperation as exc:
        raise ValueError(f"{field_label} must be a valid amount.") from exc


def _format_cents(cents):
    if cents is None:
        return ""
    return f"{cents / 100:.2f}"


def _build_form_values(profile, saved_values=None):
    saved_values = saved_values or {}
    form_values = {
        "private_reserve_balance": _format_cents(saved_values.get("private_reserve_balance")),
        "trust_home_value": _format_cents(saved_values.get("trust_home_value")),
        "accounts": {},
        "liabilities": {},
    }

    for account in profile["accounts"]:
        saved = saved_values.get("accounts", {}).get(account["id"], {})
        form_values["accounts"][account["id"]] = {
            "balance": _format_cents(saved.get("balance_cents")),
            "cash": _format_cents(saved.get("cash_balance_cents")),
        }

    for liability in profile["liabilities"]:
        saved = saved_values.get("liabilities", {}).get(liability["id"], {})
        form_values["liabilities"][liability["id"]] = {
            "balance": _format_cents(saved.get("balance_cents"))
        }

    return form_values


@bp.route("/<int:client_id>/generate", methods=["POST"])
def generate(client_id):
    today = datetime.today()
    period = f"Q{(today.month-1)//3 + 1} {today.year}"
    report_id = repository.create_report(client_id, today.strftime("%Y-%m-%d"), period)
    flash("Draft report created.", "success")
    return redirect(url_for("reports.entry", report_id=report_id))


@bp.route("/<int:report_id>/entry", methods=["GET", "POST"])
def entry(report_id):
    report = repository.get_by_id("reports", report_id)
    if not report:
        return "Report not found", 404

    client_id = report["client_id"]
    profile = repository.get_full_client_profile(client_id)
    saved_values = repository.get_saved_report_values(report_id)
    previous_values = repository.get_previous_report_values(client_id, before_report_id=report_id)
    form_values = _build_form_values(profile, saved_values=saved_values)

    if request.method == "POST":
        errors = []
        action = request.form.get("submit_action", "complete")

        try:
            reserve_balance = _money_to_cents(
                request.form.get("private_reserve_balance"),
                "Private Reserve Balance",
            )
        except ValueError as exc:
            errors.append(str(exc))
            reserve_balance = 0

        trust_value = 0
        if profile.get("trust"):
            try:
                trust_value = _money_to_cents(
                    request.form.get("trust_home_value"),
                    "Trust / Home Value",
                )
            except ValueError as exc:
                errors.append(str(exc))

        dynamic_scalars = {
            "private_reserve_balance_cents": reserve_balance,
            "trust_home_value_cents": trust_value,
        }

        acc_bals = {}
        for acc in profile["accounts"]:
            balance_field = f"account_{acc['id']}_balance"
            try:
                bal = _money_to_cents(request.form.get(balance_field), f"{acc['account_type']} balance")
            except ValueError as exc:
                errors.append(str(exc))
                bal = 0

            cash_bal = None
            if acc["is_investment_account"]:
                cash_field = f"account_{acc['id']}_cash"
                try:
                    cash_bal = _money_to_cents(request.form.get(cash_field), f"{acc['account_type']} cash balance")
                except ValueError as exc:
                    errors.append(str(exc))
                    cash_bal = 0

            acc_bals[acc["id"]] = {"balance_cents": bal, "cash_balance_cents": cash_bal}

        liab_bals = {}
        for liab in profile["liabilities"]:
            try:
                bal = _money_to_cents(
                    request.form.get(f"liability_{liab['id']}_balance"),
                    f"{liab['liability_type']} balance",
                )
            except ValueError as exc:
                errors.append(str(exc))
                bal = 0

            liab_bals[liab["id"]] = {
                "balance_cents": bal,
                "interest_rate_snapshot": liab["interest_rate"],
            }

        form_values = {
            "private_reserve_balance": request.form.get("private_reserve_balance", ""),
            "trust_home_value": request.form.get("trust_home_value", ""),
            "accounts": {
                acc["id"]: {
                    "balance": request.form.get(f"account_{acc['id']}_balance", ""),
                    "cash": request.form.get(f"account_{acc['id']}_cash", ""),
                }
                for acc in profile["accounts"]
            },
            "liabilities": {
                liab["id"]: {"balance": request.form.get(f"liability_{liab['id']}_balance", "")}
                for liab in profile["liabilities"]
            },
        }

        if errors:
            for error in errors:
                flash(error, "error")
        else:
            status = "complete" if action == "complete" else "draft"
            repository.save_report_balances(
                report_id,
                acc_bals,
                liab_bals,
                dynamic_scalars,
                status=status,
            )
            flash("Report saved." if status == "draft" else "Report completed and ready to export.", "success")
            if status == "complete":
                return redirect(url_for("exports.download_page", report_id=report_id))
            return redirect(url_for("reports.entry", report_id=report_id))

    excess = calculate_sacs_excess(
        report["snap_monthly_salary_cents"], report["snap_monthly_expense_budget_cents"]
    )
    reserve_target = calculate_reserve_target(
        report["snap_monthly_expense_budget_cents"],
        report["snap_insurance_deductibles_cents"],
        profile.get("reserve_target_override_cents"),
    )

    return render_template(
        "report_entry.html",
        report=report,
        profile=profile,
        excess=excess,
        reserve_target=reserve_target,
        previous_values=previous_values,
        form_values=form_values,
    )
