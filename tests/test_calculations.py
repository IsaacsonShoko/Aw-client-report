import pytest
from datetime import datetime
from calculations import (
    calculate_age,
    calculate_sacs_excess,
    calculate_reserve_target,
    calculate_client_retirement_total,
    calculate_non_retirement_total,
    calculate_net_worth,
    calculate_liabilities_total
)
from config import Config

def test_calculate_age():
    assert calculate_age('1980-05-15', '2026-06-17') == 46
    assert calculate_age('1980-08-15', '2026-06-17') == 45

def test_calculate_sacs_excess():
    assert calculate_sacs_excess(1000000, 400000) == 600000

def test_calculate_reserve_target_no_override():
    # 6 * 400000 + 50000 = 2400000 + 50000 = 2450000
    assert calculate_reserve_target(400000, 50000) == 2450000

def test_calculate_reserve_target_with_override():
    assert calculate_reserve_target(400000, 50000, override_cents=3000000) == 3000000

def test_calculate_reserve_target_floor():
    Config.RESERVE_FLOOR_CENTS = 100000
    assert calculate_reserve_target(1000, 0) == 100000

def test_calculate_client_retirement_total():
    accounts = [
        {'id': 1, 'person_id': 1, 'category': 'retirement'},
        {'id': 2, 'person_id': 1, 'category': 'retirement'},
        {'id': 3, 'person_id': 2, 'category': 'retirement'},
        {'id': 4, 'person_id': 1, 'category': 'non_retirement'},
    ]
    balances = {1: 5000, 2: 15000, 3: 20000, 4: 8000}
    assert calculate_client_retirement_total(accounts, balances, 1) == 20000
    assert calculate_client_retirement_total(accounts, balances, 2) == 20000

def test_calculate_non_retirement_total():
    accounts = [
        {'id': 1, 'person_id': 1, 'category': 'retirement'},
        {'id': 2, 'person_id': None, 'category': 'non_retirement'},
        {'id': 3, 'person_id': None, 'category': 'non_retirement'},
    ]
    balances = {1: 5000, 2: 15000, 3: 20000}
    assert calculate_non_retirement_total(accounts, balances) == 35000

def test_calculate_net_worth():
    assert calculate_net_worth(20000, 20000, 35000, 100000) == 175000

def test_calculate_liabilities_total():
    liabilities = [{'id': 1}, {'id': 2}]
    balances = {1: 50000, 2: 150000}
    assert calculate_liabilities_total(liabilities, balances) == 200000
