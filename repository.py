import pymysql
import pymysql.cursors
from urllib.parse import urlparse
import os
from dotenv import load_dotenv
from datetime import date, datetime

load_dotenv()

def _connection_kwargs_from_url(mysql_url):
    parsed = urlparse(mysql_url)
    return {
        'host': parsed.hostname,
        'port': parsed.port or 3306,
        'user': parsed.username,
        'password': parsed.password,
        'database': parsed.path.lstrip('/'),
    }

def _get_connection_kwargs():
    # Support both local development and Railway-provided runtime variables.
    mysql_url = (
        os.environ.get('MYSQL_URL')
        or os.environ.get('MYSQL_PRIVATE_URL')
        or os.environ.get('MYSQL_PUBLIC_URL')
        or os.environ.get('DATABASE_URL')
    )
    if mysql_url:
        return _connection_kwargs_from_url(mysql_url)

    host = os.environ.get('MYSQLHOST')
    user = os.environ.get('MYSQLUSER')
    password = os.environ.get('MYSQLPASSWORD')
    database = os.environ.get('MYSQLDATABASE')

    if host and user and password and database:
        return {
            'host': host,
            'port': int(os.environ.get('MYSQLPORT', '3306')),
            'user': user,
            'password': password,
            'database': database,
        }

    raise ValueError(
        "MySQL environment variables are not set. Expected MYSQL_URL or "
        "Railway MYSQLHOST/MYSQLPORT/MYSQLUSER/MYSQLPASSWORD/MYSQLDATABASE."
    )

def get_connection():
    kwargs = _get_connection_kwargs()
    return pymysql.connect(
        host=kwargs['host'],
        port=kwargs['port'],
        user=kwargs['user'],
        password=kwargs['password'],
        database=kwargs['database'],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True
    )

def _serialize(record):
    if not record:
        return record
    res = {}
    for k, v in record.items():
        if isinstance(v, (date, datetime)):
            res[k] = v.isoformat()
        else:
            res[k] = v
    return res

def _serialize_list(records):
    return [_serialize(r) for r in records]

def insert(table, record):
    conn = get_connection()
    with conn.cursor() as cursor:
        keys = list(record.keys())
        values = list(record.values())
        placeholders = ', '.join(['%s'] * len(keys))
        cols = ', '.join(keys)
        sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"
        cursor.execute(sql, values)
        return cursor.lastrowid

def get_all(table):
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT * FROM {table}")
        return _serialize_list(cursor.fetchall())

def get_by_id(table, record_id):
    conn = get_connection()
    with conn.cursor() as cursor:
        cursor.execute(f"SELECT * FROM {table} WHERE id = %s", (record_id,))
        return _serialize(cursor.fetchone())

def get_where(table, **kwargs):
    conn = get_connection()
    with conn.cursor() as cursor:
        keys = list(kwargs.keys())
        values = list(kwargs.values())
        conditions = ' AND '.join([f"{k} = %s" for k in keys])
        sql = f"SELECT * FROM {table} WHERE {conditions}"
        cursor.execute(sql, values)
        return _serialize_list(cursor.fetchall())

def update(table, record_id, updates):
    conn = get_connection()
    with conn.cursor() as cursor:
        keys = list(updates.keys())
        values = list(updates.values())
        set_clause = ', '.join([f"{k} = %s" for k in keys])
        sql = f"UPDATE {table} SET {set_clause} WHERE id = %s"
        values.append(record_id)
        cursor.execute(sql, values)
    return get_by_id(table, record_id)

# Helpers for the app
def get_clients_with_last_report():
    conn = get_connection()
    with conn.cursor() as cursor:
        sql = """
            SELECT c.*, MAX(r.report_date) as last_report_date
            FROM clients c
            LEFT JOIN reports r ON c.id = r.client_id
            GROUP BY c.id
        """
        cursor.execute(sql)
        return _serialize_list(cursor.fetchall())

def get_full_client_profile(client_id):
    client = get_by_id('clients', client_id)
    if not client: return None
    
    client['persons'] = get_where('persons', client_id=client_id)
    client['accounts'] = get_where('accounts', client_id=client_id)
    trusts = get_where('trusts', client_id=client_id)
    client['trust'] = trusts[0] if trusts else None
    client['liabilities'] = get_where('liabilities', client_id=client_id)
    return client

def create_report(client_id, report_date, report_period):
    client = get_by_id('clients', client_id)
    report_data = {
        'client_id': client_id,
        'report_date': report_date,
        'report_period': report_period,
        'status': 'draft',
        'private_reserve_balance_cents': 0,
        'trust_home_value_cents': 0,
        'snap_monthly_salary_cents': client['monthly_salary_cents'],
        'snap_monthly_expense_budget_cents': client['monthly_expense_budget_cents'],
        'snap_insurance_deductibles_cents': client['insurance_deductibles_cents'],
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    return insert('reports', report_data)

def save_report_balances(report_id, account_balances, liability_balances, dynamic_scalars):
    dynamic_scalars['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    update('reports', report_id, dynamic_scalars)
    
    for acc_id, bals in account_balances.items():
        existing = get_where('report_account_balances', report_id=report_id, account_id=acc_id)
        if existing:
            update('report_account_balances', existing[0]['id'], bals)
        else:
            rec = {'report_id': report_id, 'account_id': acc_id, **bals}
            insert('report_account_balances', rec)
            
    for liab_id, bals in liability_balances.items():
        existing = get_where('report_liability_balances', report_id=report_id, liability_id=liab_id)
        if existing:
            update('report_liability_balances', existing[0]['id'], bals)
        else:
            rec = {'report_id': report_id, 'liability_id': liab_id, **bals}
            insert('report_liability_balances', rec)
    
    update('reports', report_id, {'status': 'complete'})
