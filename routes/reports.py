from flask import Blueprint, render_template, request, redirect, url_for
from datetime import datetime
import repository
from calculations import calculate_reserve_target, calculate_sacs_excess

bp = Blueprint('reports', __name__, url_prefix='/reports')

@bp.route('/<int:client_id>/generate', methods=['POST'])
def generate(client_id):
    today = datetime.today()
    period = f"Q{(today.month-1)//3 + 1} {today.year}"
    report_id = repository.create_report(client_id, today.strftime('%Y-%m-%d'), period)
    return redirect(url_for('reports.entry', report_id=report_id))

@bp.route('/<int:report_id>/entry', methods=['GET', 'POST'])
def entry(report_id):
    report = repository.get_by_id('reports', report_id)
    if not report:
        return "Report not found", 404
        
    client_id = report['client_id']
    profile = repository.get_full_client_profile(client_id)
    
    if request.method == 'POST':
        # Parse dynamic scalars
        reserve_balance = int(float(request.form.get('private_reserve_balance', 0)) * 100)
        trust_value = int(float(request.form.get('trust_home_value', 0)) * 100)
        
        dynamic_scalars = {
            'private_reserve_balance_cents': reserve_balance,
            'trust_home_value_cents': trust_value
        }
        
        # Parse accounts
        acc_bals = {}
        for acc in profile['accounts']:
            bal = int(float(request.form.get(f"account_{acc['id']}_balance", 0)) * 100)
            cash_bal = None
            if acc['is_investment_account']:
                cash_bal = int(float(request.form.get(f"account_{acc['id']}_cash", 0)) * 100)
            acc_bals[acc['id']] = {'balance_cents': bal, 'cash_balance_cents': cash_bal}
            
        # Parse liabilities
        liab_bals = {}
        for liab in profile['liabilities']:
            bal = int(float(request.form.get(f"liability_{liab['id']}_balance", 0)) * 100)
            liab_bals[liab['id']] = {
                'balance_cents': bal,
                'interest_rate_snapshot': liab['interest_rate']
            }
            
        repository.save_report_balances(report_id, acc_bals, liab_bals, dynamic_scalars)
        return redirect(url_for('exports.download_page', report_id=report_id))
        
    # GET: Prepare data for entry form
    excess = calculate_sacs_excess(report['snap_monthly_salary_cents'], report['snap_monthly_expense_budget_cents'])
    reserve_target = calculate_reserve_target(
        report['snap_monthly_expense_budget_cents'], 
        report['snap_insurance_deductibles_cents'], 
        profile.get('reserve_target_override_cents')
    )
    
    return render_template('report_entry.html', 
        report=report, 
        profile=profile,
        excess=excess,
        reserve_target=reserve_target
    )
