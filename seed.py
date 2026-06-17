from repository import insert

def seed_data():
    # Client 1: Married couple
    client1_id = insert('clients', {
        'household_name': 'Smith Family',
        'marital_status': 'married',
        'monthly_salary_cents': 2000000, # $20,000
        'monthly_expense_budget_cents': 1200000, # $12,000
        'insurance_deductibles_cents': 500000, # $5,000
        'reserve_target_override_cents': None,
        'created_at': '2026-06-01 00:00:00',
        'updated_at': '2026-06-01 00:00:00'
    })
    
    p1_id = insert('persons', {
        'client_id': client1_id,
        'person_role': 'client_1',
        'first_name': 'John',
        'last_name': 'Smith',
        'date_of_birth': '1975-04-12',
        'ssn_last_four': '1234'
    })
    
    p2_id = insert('persons', {
        'client_id': client1_id,
        'person_role': 'client_2',
        'first_name': 'Jane',
        'last_name': 'Smith',
        'date_of_birth': '1978-08-22',
        'ssn_last_four': '5678'
    })
    
    # Accounts for Client 1
    insert('accounts', {
        'client_id': client1_id, 'person_id': p1_id, 'category': 'retirement',
        'account_type': 'IRA', 'account_number_last_four': '1111', 'institution': 'Schwab', 'is_investment_account': 1
    })
    insert('accounts', {
        'client_id': client1_id, 'person_id': p1_id, 'category': 'retirement',
        'account_type': 'Roth IRA', 'account_number_last_four': '2222', 'institution': 'Schwab', 'is_investment_account': 1
    })
    insert('accounts', {
        'client_id': client1_id, 'person_id': p2_id, 'category': 'retirement',
        'account_type': '401K', 'account_number_last_four': '3333', 'institution': 'Fidelity', 'is_investment_account': 1
    })
    insert('accounts', {
        'client_id': client1_id, 'person_id': None, 'category': 'non_retirement',
        'account_type': 'Joint Brokerage', 'account_number_last_four': '4444', 'institution': 'Schwab', 'is_investment_account': 1
    })
    
    # Trust and Liabilities
    insert('trusts', {
        'client_id': client1_id,
        'property_address': '123 Maple Street, Atlanta GA'
    })
    insert('liabilities', {
        'client_id': client1_id, 'liability_type': 'Mortgage', 'description': 'Primary Residence', 'interest_rate': 3.5
    })
    
    # Client 2: Single
    client2_id = insert('clients', {
        'household_name': 'Doe',
        'marital_status': 'single',
        'monthly_salary_cents': 1500000,
        'monthly_expense_budget_cents': 800000,
        'insurance_deductibles_cents': 200000,
        'reserve_target_override_cents': None,
        'created_at': '2026-06-10 00:00:00',
        'updated_at': '2026-06-10 00:00:00'
    })
    
    p3_id = insert('persons', {
        'client_id': client2_id,
        'person_role': 'client_1',
        'first_name': 'Alice',
        'last_name': 'Doe',
        'date_of_birth': '1985-11-30',
        'ssn_last_four': '9999'
    })
    
    insert('accounts', {
        'client_id': client2_id, 'person_id': p3_id, 'category': 'retirement',
        'account_type': 'IRA', 'account_number_last_four': '5555', 'institution': 'Vanguard', 'is_investment_account': 1
    })
    insert('accounts', {
        'client_id': client2_id, 'person_id': p3_id, 'category': 'non_retirement',
        'account_type': 'Brokerage', 'account_number_last_four': '6666', 'institution': 'Schwab', 'is_investment_account': 1
    })
    insert('trusts', {
        'client_id': client2_id,
        'property_address': '456 Oak Ave, Atlanta GA'
    })
