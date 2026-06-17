import os
import pymysql
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

MYSQL_URL = os.environ.get('MYSQL_URL')

def init_db():
    if not MYSQL_URL:
        print("Please set MYSQL_URL in your .env file or environment.")
        return
        
    parsed = urlparse(MYSQL_URL)
    conn = pymysql.connect(
        host=parsed.hostname,
        port=parsed.port or 3306,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path.lstrip('/'),
        autocommit=True
    )
    
    with open('schema.sql', 'r') as f:
        sql_commands = f.read().split(';')
        
    with conn.cursor() as cursor:
        for cmd in sql_commands:
            if cmd.strip():
                cursor.execute(cmd)
                
    print("Schema created successfully.")
    
    # Run seed
    from seed import seed_data
    try:
        seed_data()
        print("Database seeded with sample clients.")
    except Exception as e:
        print(f"Seed failed (maybe already seeded?): {e}")

if __name__ == '__main__':
    init_db()