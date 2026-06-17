import os
from datetime import date, datetime
from urllib.parse import urlparse

import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()

PERSON_ROLE_ORDER = {"client_1": 0, "client_2": 1}


def _connection_kwargs_from_url(mysql_url):
    parsed = urlparse(mysql_url)
    return {
        "host": parsed.hostname,
        "port": parsed.port or 3306,
        "user": parsed.username,
        "password": parsed.password,
        "database": parsed.path.lstrip("/"),
    }


def _get_connection_kwargs():
    mysql_url = (
        os.environ.get("MYSQL_URL")
        or os.environ.get("MYSQL_PUBLIC_URL")
        or os.environ.get("DATABASE_URL")
    )
    if mysql_url:
        return _connection_kwargs_from_url(mysql_url)

    host = os.environ.get("MYSQLHOST")
    user = os.environ.get("MYSQLUSER")
    password = os.environ.get("MYSQLPASSWORD")
    database = os.environ.get("MYSQL_DATABASE") or os.environ.get("MYSQLDATABASE")

    if host and user and password and database:
        return {
            "host": host,
            "port": int(os.environ.get("MYSQLPORT", "3306")),
            "user": user,
            "password": password,
            "database": database,
        }

    raise ValueError(
        "MySQL environment variables are not set. Expected MYSQL_URL or "
        "Railway MYSQLHOST/MYSQLPORT/MYSQLUSER/MYSQLPASSWORD/MYSQL_DATABASE."
    )


def get_connection(autocommit=True):
    kwargs = _get_connection_kwargs()
    return pymysql.connect(
        host=kwargs["host"],
        port=kwargs["port"],
        user=kwargs["user"],
        password=kwargs["password"],
        database=kwargs["database"],
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=autocommit,
    )


def _serialize(record):
    if not record:
        return record

    serialized = {}
    for key, value in record.items():
        if isinstance(value, (date, datetime)):
            serialized[key] = value.isoformat()
        else:
            serialized[key] = value
    return serialized


def _serialize_list(records):
    return [_serialize(record) for record in records]


def insert(table, record, cursor=None):
    keys = list(record.keys())
    values = list(record.values())
    placeholders = ", ".join(["%s"] * len(keys))
    cols = ", ".join(keys)
    sql = f"INSERT INTO {table} ({cols}) VALUES ({placeholders})"

    if cursor is not None:
        cursor.execute(sql, values)
        return cursor.lastrowid

    conn = get_connection()
    try:
        with conn.cursor() as local_cursor:
            local_cursor.execute(sql, values)
            return local_cursor.lastrowid
    finally:
        conn.close()


def get_all(table):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {table}")
            return _serialize_list(cursor.fetchall())
    finally:
        conn.close()


def get_by_id(table, record_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"SELECT * FROM {table} WHERE id = %s", (record_id,))
            return _serialize(cursor.fetchone())
    finally:
        conn.close()


def get_where(table, **kwargs):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            keys = list(kwargs.keys())
            values = list(kwargs.values())
            conditions = " AND ".join([f"{key} = %s" for key in keys])
            sql = f"SELECT * FROM {table} WHERE {conditions}"
            cursor.execute(sql, values)
            return _serialize_list(cursor.fetchall())
    finally:
        conn.close()


def update(table, record_id, updates, cursor=None):
    keys = list(updates.keys())
    values = list(updates.values())
    set_clause = ", ".join([f"{key} = %s" for key in keys])
    sql = f"UPDATE {table} SET {set_clause} WHERE id = %s"
    values.append(record_id)

    if cursor is not None:
        cursor.execute(sql, values)
        return record_id

    conn = get_connection()
    try:
        with conn.cursor() as local_cursor:
            local_cursor.execute(sql, values)
        return get_by_id(table, record_id)
    finally:
        conn.close()


def _fetchall(cursor, sql, params=None):
    cursor.execute(sql, params or ())
    return _serialize_list(cursor.fetchall())


def _fetchone(cursor, sql, params=None):
    cursor.execute(sql, params or ())
    return _serialize(cursor.fetchone())


def _get_persons(cursor, client_id):
    persons = _fetchall(
        cursor,
        """
        SELECT *
        FROM persons
        WHERE client_id = %s
        ORDER BY FIELD(person_role, 'client_1', 'client_2'), id
        """,
        (client_id,),
    )
    return persons


def _get_accounts(cursor, client_id, include_inactive=False, include_account_ids=None):
    clauses = ["client_id = %s"]
    params = [client_id]

    if include_inactive:
        pass
    elif include_account_ids:
        placeholders = ", ".join(["%s"] * len(include_account_ids))
        clauses.append(f"(active = 1 OR id IN ({placeholders}))")
        params.extend(include_account_ids)
    else:
        clauses.append("active = 1")

    sql = f"""
        SELECT *
        FROM accounts
        WHERE {' AND '.join(clauses)}
        ORDER BY category, display_order, id
    """
    return _fetchall(cursor, sql, params)


def _get_liabilities(cursor, client_id, include_inactive=False, include_liability_ids=None):
    clauses = ["client_id = %s"]
    params = [client_id]

    if include_inactive:
        pass
    elif include_liability_ids:
        placeholders = ", ".join(["%s"] * len(include_liability_ids))
        clauses.append(f"(active = 1 OR id IN ({placeholders}))")
        params.extend(include_liability_ids)
    else:
        clauses.append("active = 1")

    sql = f"""
        SELECT *
        FROM liabilities
        WHERE {' AND '.join(clauses)}
        ORDER BY display_order, id
    """
    return _fetchall(cursor, sql, params)


def _get_trust(cursor, client_id):
    return _fetchone(
        cursor,
        "SELECT * FROM trusts WHERE client_id = %s LIMIT 1",
        (client_id,),
    )


def _build_profile(
    cursor,
    client_id,
    include_inactive=False,
    include_account_ids=None,
    include_liability_ids=None,
):
    client = _fetchone(cursor, "SELECT * FROM clients WHERE id = %s", (client_id,))
    if not client:
        return None

    persons = _get_persons(cursor, client_id)
    if client["marital_status"] == "single":
        persons = [person for person in persons if person["person_role"] == "client_1"]

    client["persons"] = persons
    client["accounts"] = _get_accounts(
        cursor,
        client_id,
        include_inactive=include_inactive,
        include_account_ids=include_account_ids,
    )
    client["trust"] = _get_trust(cursor, client_id)
    client["liabilities"] = _get_liabilities(
        cursor,
        client_id,
        include_inactive=include_inactive,
        include_liability_ids=include_liability_ids,
    )
    return client


def get_clients_with_last_report():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT c.*, MAX(r.report_date) AS last_report_date, COUNT(r.id) AS report_count
                FROM clients c
                LEFT JOIN reports r ON c.id = r.client_id
                GROUP BY c.id
                ORDER BY c.household_name
            """
            cursor.execute(sql)
            return _serialize_list(cursor.fetchall())
    finally:
        conn.close()


def get_full_client_profile(client_id, include_inactive=False):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            return _build_profile(cursor, client_id, include_inactive=include_inactive)
    finally:
        conn.close()


def get_client_detail(client_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            profile = _build_profile(cursor, client_id)
            if not profile:
                return None
            profile["reports"] = _fetchall(
                cursor,
                """
                SELECT id, report_date, report_period, status, updated_at
                FROM reports
                WHERE client_id = %s
                ORDER BY report_date DESC, id DESC
                """,
                (client_id,),
            )
            return profile
    finally:
        conn.close()


def _upsert_person(cursor, client_id, role, person_data):
    existing = _fetchone(
        cursor,
        "SELECT * FROM persons WHERE client_id = %s AND person_role = %s",
        (client_id, role),
    )

    payload = {
        "client_id": client_id,
        "person_role": role,
        "first_name": person_data["first_name"],
        "last_name": person_data["last_name"],
        "date_of_birth": person_data["date_of_birth"],
        "ssn_last_four": person_data["ssn_last_four"],
    }

    if existing:
        update(
            "persons",
            existing["id"],
            {
                "first_name": payload["first_name"],
                "last_name": payload["last_name"],
                "date_of_birth": payload["date_of_birth"],
                "ssn_last_four": payload["ssn_last_four"],
            },
            cursor=cursor,
        )
        return existing["id"]

    return insert("persons", payload, cursor=cursor)


def _sync_accounts(cursor, client_id, submitted_accounts, person_ids):
    existing_accounts = _fetchall(
        cursor,
        "SELECT * FROM accounts WHERE client_id = %s",
        (client_id,),
    )
    existing_by_id = {account["id"]: account for account in existing_accounts}
    kept_ids = []

    for display_order, account in enumerate(submitted_accounts):
        person_id = None
        owner_role = account.get("owner_role")
        if owner_role in person_ids:
            person_id = person_ids[owner_role]

        payload = {
            "client_id": client_id,
            "person_id": person_id,
            "category": account["category"],
            "account_type": account["account_type"],
            "account_number_last_four": account.get("account_number_last_four") or None,
            "institution": account.get("institution") or None,
            "is_investment_account": 1 if account.get("is_investment_account") else 0,
            "display_order": display_order,
            "active": 1,
        }

        account_id = account.get("id")
        if account_id and account_id in existing_by_id:
            update("accounts", account_id, payload, cursor=cursor)
            kept_ids.append(account_id)
        else:
            kept_ids.append(insert("accounts", payload, cursor=cursor))

    for existing in existing_accounts:
        if existing["id"] not in kept_ids and existing["active"]:
            update(
                "accounts",
                existing["id"],
                {"active": 0, "display_order": existing["display_order"]},
                cursor=cursor,
            )


def _sync_liabilities(cursor, client_id, submitted_liabilities):
    existing_liabilities = _fetchall(
        cursor,
        "SELECT * FROM liabilities WHERE client_id = %s",
        (client_id,),
    )
    existing_by_id = {liability["id"]: liability for liability in existing_liabilities}
    kept_ids = []

    for display_order, liability in enumerate(submitted_liabilities):
        payload = {
            "client_id": client_id,
            "liability_type": liability["liability_type"],
            "description": liability.get("description") or None,
            "interest_rate": liability.get("interest_rate"),
            "display_order": display_order,
            "active": 1,
        }

        liability_id = liability.get("id")
        if liability_id and liability_id in existing_by_id:
            update("liabilities", liability_id, payload, cursor=cursor)
            kept_ids.append(liability_id)
        else:
            kept_ids.append(insert("liabilities", payload, cursor=cursor))

    for existing in existing_liabilities:
        if existing["id"] not in kept_ids and existing["active"]:
            update(
                "liabilities",
                existing["id"],
                {"active": 0, "display_order": existing["display_order"]},
                cursor=cursor,
            )


def _sync_trust(cursor, client_id, property_address):
    existing = _fetchone(
        cursor,
        "SELECT * FROM trusts WHERE client_id = %s LIMIT 1",
        (client_id,),
    )
    cleaned_address = (property_address or "").strip()

    if cleaned_address:
        if existing:
            update(
                "trusts",
                existing["id"],
                {"property_address": cleaned_address},
                cursor=cursor,
            )
        else:
            insert(
                "trusts",
                {"client_id": client_id, "property_address": cleaned_address},
                cursor=cursor,
            )


def create_client_profile(payload):
    conn = get_connection(autocommit=False)
    try:
        with conn.cursor() as cursor:
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            client_id = insert(
                "clients",
                {
                    "household_name": payload["household_name"],
                    "marital_status": payload["marital_status"],
                    "monthly_salary_cents": payload["monthly_salary_cents"],
                    "monthly_expense_budget_cents": payload["monthly_expense_budget_cents"],
                    "insurance_deductibles_cents": payload["insurance_deductibles_cents"],
                    "reserve_target_override_cents": payload["reserve_target_override_cents"],
                    "created_at": now,
                    "updated_at": now,
                },
                cursor=cursor,
            )

            person_ids = {}
            for role, person_data in payload["persons"].items():
                person_ids[role] = _upsert_person(cursor, client_id, role, person_data)

            _sync_accounts(cursor, client_id, payload["accounts"], person_ids)
            _sync_liabilities(cursor, client_id, payload["liabilities"])
            _sync_trust(cursor, client_id, payload.get("trust_property_address"))
            conn.commit()
            return client_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def update_client_profile(client_id, payload):
    conn = get_connection(autocommit=False)
    try:
        with conn.cursor() as cursor:
            update(
                "clients",
                client_id,
                {
                    "household_name": payload["household_name"],
                    "marital_status": payload["marital_status"],
                    "monthly_salary_cents": payload["monthly_salary_cents"],
                    "monthly_expense_budget_cents": payload["monthly_expense_budget_cents"],
                    "insurance_deductibles_cents": payload["insurance_deductibles_cents"],
                    "reserve_target_override_cents": payload["reserve_target_override_cents"],
                    "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                },
                cursor=cursor,
            )

            person_ids = {}
            for role, person_data in payload["persons"].items():
                person_ids[role] = _upsert_person(cursor, client_id, role, person_data)

            _sync_accounts(cursor, client_id, payload["accounts"], person_ids)
            _sync_liabilities(cursor, client_id, payload["liabilities"])
            _sync_trust(cursor, client_id, payload.get("trust_property_address"))
            conn.commit()
            return client_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def create_report(client_id, report_date, report_period):
    client = get_by_id("clients", client_id)
    report_data = {
        "client_id": client_id,
        "report_date": report_date,
        "report_period": report_period,
        "status": "draft",
        "private_reserve_balance_cents": None,
        "trust_home_value_cents": None,
        "snap_monthly_salary_cents": client["monthly_salary_cents"],
        "snap_monthly_expense_budget_cents": client["monthly_expense_budget_cents"],
        "snap_insurance_deductibles_cents": client["insurance_deductibles_cents"],
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    return insert("reports", report_data)


def get_saved_report_values(report_id):
    report = get_by_id("reports", report_id)
    if not report:
        return None

    saved_values = {
        "private_reserve_balance": report.get("private_reserve_balance_cents"),
        "trust_home_value": report.get("trust_home_value_cents"),
        "accounts": {},
        "liabilities": {},
    }

    for balance in get_where("report_account_balances", report_id=report_id):
        saved_values["accounts"][balance["account_id"]] = {
            "balance_cents": balance["balance_cents"],
            "cash_balance_cents": balance.get("cash_balance_cents"),
        }

    for balance in get_where("report_liability_balances", report_id=report_id):
        saved_values["liabilities"][balance["liability_id"]] = {
            "balance_cents": balance["balance_cents"],
        }

    return saved_values


def get_previous_report_values(client_id, before_report_id=None):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            params = [client_id]
            extra = ""
            if before_report_id:
                extra = "AND id <> %s"
                params.append(before_report_id)

            previous_report = _fetchone(
                cursor,
                f"""
                SELECT *
                FROM reports
                WHERE client_id = %s AND status = 'complete' {extra}
                ORDER BY report_date DESC, id DESC
                LIMIT 1
                """,
                params,
            )

            if not previous_report:
                return None

            previous = {
                "report_id": previous_report["id"],
                "report_period": previous_report["report_period"],
                "private_reserve_balance": previous_report.get("private_reserve_balance_cents"),
                "trust_home_value": previous_report.get("trust_home_value_cents"),
                "accounts": {},
                "liabilities": {},
            }

            account_balances = _fetchall(
                cursor,
                """
                SELECT account_id, balance_cents, cash_balance_cents
                FROM report_account_balances
                WHERE report_id = %s
                """,
                (previous_report["id"],),
            )
            for balance in account_balances:
                previous["accounts"][balance["account_id"]] = {
                    "balance_cents": balance["balance_cents"],
                    "cash_balance_cents": balance.get("cash_balance_cents"),
                }

            liability_balances = _fetchall(
                cursor,
                """
                SELECT liability_id, balance_cents
                FROM report_liability_balances
                WHERE report_id = %s
                """,
                (previous_report["id"],),
            )
            for balance in liability_balances:
                previous["liabilities"][balance["liability_id"]] = {
                    "balance_cents": balance["balance_cents"]
                }

            return previous
    finally:
        conn.close()


def get_report_profile(report_id):
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            report = _fetchone(cursor, "SELECT * FROM reports WHERE id = %s", (report_id,))
            if not report:
                return None

            account_rows = _fetchall(
                cursor,
                "SELECT account_id FROM report_account_balances WHERE report_id = %s",
                (report_id,),
            )
            liability_rows = _fetchall(
                cursor,
                "SELECT liability_id FROM report_liability_balances WHERE report_id = %s",
                (report_id,),
            )

            account_ids = [row["account_id"] for row in account_rows]
            liability_ids = [row["liability_id"] for row in liability_rows]
            return _build_profile(
                cursor,
                report["client_id"],
                include_account_ids=account_ids,
                include_liability_ids=liability_ids,
            )
    finally:
        conn.close()


def save_report_balances(report_id, account_balances, liability_balances, dynamic_scalars, status="complete"):
    conn = get_connection(autocommit=False)
    try:
        with conn.cursor() as cursor:
            dynamic_scalars["updated_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            dynamic_scalars["status"] = status
            update("reports", report_id, dynamic_scalars, cursor=cursor)

            for account_id, balances in account_balances.items():
                existing = _fetchone(
                    cursor,
                    """
                    SELECT *
                    FROM report_account_balances
                    WHERE report_id = %s AND account_id = %s
                    """,
                    (report_id, account_id),
                )
                if existing:
                    update("report_account_balances", existing["id"], balances, cursor=cursor)
                else:
                    insert(
                        "report_account_balances",
                        {"report_id": report_id, "account_id": account_id, **balances},
                        cursor=cursor,
                    )

            for liability_id, balances in liability_balances.items():
                existing = _fetchone(
                    cursor,
                    """
                    SELECT *
                    FROM report_liability_balances
                    WHERE report_id = %s AND liability_id = %s
                    """,
                    (report_id, liability_id),
                )
                if existing:
                    update("report_liability_balances", existing["id"], balances, cursor=cursor)
                else:
                    insert(
                        "report_liability_balances",
                        {"report_id": report_id, "liability_id": liability_id, **balances},
                        cursor=cursor,
                    )

            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
