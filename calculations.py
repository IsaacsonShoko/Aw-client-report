from datetime import datetime
from config import Config

def calculate_age(dob_str, target_date_str):
    dob = datetime.fromisoformat(dob_str)
    target = datetime.fromisoformat(target_date_str)
    age = target.year - dob.year - ((target.month, target.day) < (dob.month, dob.day))
    return age

def calculate_sacs_excess(inflow_cents, outflow_cents):
    return inflow_cents - outflow_cents

def calculate_reserve_target(monthly_expenses_cents, insurance_deductibles_cents, override_cents=None):
    if override_cents is not None:
        return max(override_cents, Config.RESERVE_FLOOR_CENTS)
    
    calculated = (6 * monthly_expenses_cents) + insurance_deductibles_cents
    return max(calculated, Config.RESERVE_FLOOR_CENTS)

def calculate_client_retirement_total(accounts, balances, person_id):
    """
    accounts: list of dicts like {'id': 1, 'person_id': 1, 'category': 'retirement'}
    balances: dict mapping account_id -> balance_cents
    """
    total = 0
    for acc in accounts:
        if acc['category'] == 'retirement' and acc['person_id'] == person_id:
            total += balances.get(acc['id'], 0)
    return total

def calculate_non_retirement_total(accounts, balances):
    """
    Sum of non-retirement account balances. The trust is NOT an account, so it's naturally excluded.
    """
    total = 0
    for acc in accounts:
        if acc['category'] == 'non_retirement':
            total += balances.get(acc['id'], 0)
    return total

def calculate_net_worth(client1_ret_cents, client2_ret_cents, non_ret_cents, trust_value_cents):
    return client1_ret_cents + client2_ret_cents + non_ret_cents + trust_value_cents

def calculate_liabilities_total(liabilities, balances):
    """
    liabilities: list of dicts like {'id': 1, 'liability_type': 'mortgage'}
    balances: dict mapping liability_id -> balance_cents
    """
    total = 0
    for liab in liabilities:
        total += balances.get(liab['id'], 0)
    return total
