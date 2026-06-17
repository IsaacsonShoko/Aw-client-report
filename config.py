import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-key-for-sagan-test')
    MYSQL_URL = os.environ.get('MYSQL_URL')
    CANVA_API_KEY = os.environ.get('CANVA_API_KEY')
    
    # Global constants from PRD
    RESERVE_FLOOR_CENTS = 100000  # $1,000 floor
