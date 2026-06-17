CREATE TABLE IF NOT EXISTS clients (
    id INT AUTO_INCREMENT PRIMARY KEY,
    household_name VARCHAR(255),
    marital_status ENUM('single', 'married') NOT NULL,
    monthly_salary_cents INT NOT NULL,
    monthly_expense_budget_cents INT NOT NULL,
    insurance_deductibles_cents INT NOT NULL DEFAULT 0,
    reserve_target_override_cents INT,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS persons (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    person_role ENUM('client_1', 'client_2') NOT NULL,
    first_name VARCHAR(255) NOT NULL,
    last_name VARCHAR(255) NOT NULL,
    date_of_birth DATE NOT NULL,
    ssn_last_four VARCHAR(4) NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id),
    UNIQUE (client_id, person_role)
);

CREATE TABLE IF NOT EXISTS accounts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    person_id INT,
    category ENUM('retirement', 'non_retirement') NOT NULL,
    account_type VARCHAR(255) NOT NULL,
    account_number_last_four VARCHAR(4),
    institution VARCHAR(255),
    is_investment_account TINYINT(1) NOT NULL DEFAULT 0,
    display_order INT NOT NULL DEFAULT 0,
    active TINYINT(1) NOT NULL DEFAULT 1,
    FOREIGN KEY (client_id) REFERENCES clients(id),
    FOREIGN KEY (person_id) REFERENCES persons(id)
);

CREATE TABLE IF NOT EXISTS trusts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL UNIQUE,
    property_address TEXT NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE TABLE IF NOT EXISTS liabilities (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    liability_type VARCHAR(255) NOT NULL,
    description TEXT,
    interest_rate DECIMAL(5,2),
    display_order INT NOT NULL DEFAULT 0,
    active TINYINT(1) NOT NULL DEFAULT 1,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE TABLE IF NOT EXISTS reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    client_id INT NOT NULL,
    report_date DATE NOT NULL,
    report_period VARCHAR(50),
    status ENUM('draft', 'complete') NOT NULL DEFAULT 'draft',
    private_reserve_balance_cents INT,
    trust_home_value_cents INT,
    snap_monthly_salary_cents INT NOT NULL,
    snap_monthly_expense_budget_cents INT NOT NULL,
    snap_insurance_deductibles_cents INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL,
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE TABLE IF NOT EXISTS report_account_balances (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_id INT NOT NULL,
    account_id INT NOT NULL,
    balance_cents INT NOT NULL,
    cash_balance_cents INT,
    FOREIGN KEY (report_id) REFERENCES reports(id),
    FOREIGN KEY (account_id) REFERENCES accounts(id),
    UNIQUE (report_id, account_id)
);

CREATE TABLE IF NOT EXISTS report_liability_balances (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_id INT NOT NULL,
    liability_id INT NOT NULL,
    balance_cents INT NOT NULL,
    interest_rate_snapshot DECIMAL(5,2),
    FOREIGN KEY (report_id) REFERENCES reports(id),
    FOREIGN KEY (liability_id) REFERENCES liabilities(id),
    UNIQUE (report_id, liability_id)
);
