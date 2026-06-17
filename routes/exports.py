import io
import zipfile

from flask import Blueprint, current_app, flash, redirect, render_template, request, send_file, url_for

import repository
from calculations import (
    calculate_age,
    calculate_reserve_target,
    calculate_client_retirement_total,
    calculate_non_retirement_total,
    calculate_net_worth,
    calculate_liabilities_total
)

bp = Blueprint("exports", __name__, url_prefix="/exports")


def render_pdf_bytes(html_string, base_url):
    try:
        from weasyprint import HTML
    except OSError as exc:
        # Delay native library loading until PDF generation so the app can boot.
        raise RuntimeError(
            "WeasyPrint native libraries are missing on the host. "
            "Install the required Pango/GLib packages for PDF generation."
        ) from exc

    return HTML(string=html_string, base_url=base_url).write_pdf()


def _render_sacs_pdf(report_id, base_url):
    ctx = get_report_context(report_id)
    html_string = render_template("reports/sacs.html", **ctx)
    pdf = render_pdf_bytes(html_string, base_url)
    filename = f"SACS_{ctx['profile']['household_name']}_{ctx['report']['report_period']}.pdf"
    return pdf, filename


def _render_tcc_pdf(report_id, base_url):
    ctx = get_report_context(report_id)
    html_string = render_template("reports/tcc.html", **ctx)
    pdf = render_pdf_bytes(html_string, base_url)
    filename = f"TCC_{ctx['profile']['household_name']}_{ctx['report']['report_period']}.pdf"
    return pdf, filename


@bp.route("/<int:report_id>")
def download_page(report_id):
    report = repository.get_by_id("reports", report_id)
    if not report:
        return "Report not found", 404

    return render_template(
        "download.html",
        report_id=report_id,
        report=report,
        canva_enabled=bool(current_app.config.get("CANVA_API_KEY")),
    )


def get_report_context(report_id):
    report = repository.get_by_id("reports", report_id)
    profile = repository.get_report_profile(report_id)

    reserve_target = calculate_reserve_target(
        report["snap_monthly_expense_budget_cents"],
        report["snap_insurance_deductibles_cents"],
        profile.get("reserve_target_override_cents"),
    )

    acc_balances = {}
    report_acc_bals = repository.get_where("report_account_balances", report_id=report_id)
    for rab in report_acc_bals:
        acc_balances[rab["account_id"]] = rab["balance_cents"]

    liab_balances = {}
    report_liab_bals = repository.get_where("report_liability_balances", report_id=report_id)
    for rlb in report_liab_bals:
        liab_balances[rlb["liability_id"]] = rlb["balance_cents"]

    ret_totals = {}
    for person in profile["persons"]:
        ret_totals[person["id"]] = calculate_client_retirement_total(
            profile["accounts"], acc_balances, person["id"]
        )

    non_ret_total = calculate_non_retirement_total(profile["accounts"], acc_balances)

    net_worth = calculate_net_worth(
        sum(ret_totals.values()),
        0,
        non_ret_total,
        report["trust_home_value_cents"],
    )

    liabilities_total = calculate_liabilities_total(profile["liabilities"], liab_balances)

    return {
        "report": report,
        "profile": profile,
        "reserve_target": reserve_target,
        "balances": acc_balances,
        "liab_balances": liab_balances,
        "ret_totals": ret_totals,
        "non_ret_total": non_ret_total,
        "net_worth": net_worth,
        "liabilities_total": liabilities_total,
        "calculate_age": calculate_age,
    }


@bp.route("/<int:report_id>/sacs.pdf")
def download_sacs(report_id):
    pdf, filename = _render_sacs_pdf(report_id, request.url_root)

    return send_file(
        io.BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@bp.route("/<int:report_id>/tcc.pdf")
def download_tcc(report_id):
    pdf, filename = _render_tcc_pdf(report_id, request.url_root)

    return send_file(
        io.BytesIO(pdf),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@bp.route("/<int:report_id>/all.zip")
def download_all(report_id):
    sacs_pdf, sacs_name = _render_sacs_pdf(report_id, request.url_root)
    tcc_pdf, tcc_name = _render_tcc_pdf(report_id, request.url_root)
    report = repository.get_by_id("reports", report_id)
    client = repository.get_by_id("clients", report["client_id"])

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        zip_file.writestr(sacs_name, sacs_pdf)
        zip_file.writestr(tcc_name, tcc_pdf)

    zip_buffer.seek(0)
    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"{client['household_name']}_{report['report_period']}_reports.zip",
    )


@bp.route("/<int:report_id>/export-canva", methods=["POST"])
def export_canva(report_id):
    if not current_app.config.get("CANVA_API_KEY"):
        flash("Canva export is disabled. Add CANVA_API_KEY to enable it.", "error")
        return redirect(url_for("exports.download_page", report_id=report_id))

    flash("Canva export is enabled in config, but the integration endpoint is still a placeholder.", "error")
    return redirect(url_for("exports.download_page", report_id=report_id))
