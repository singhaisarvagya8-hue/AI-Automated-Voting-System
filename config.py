import os

# Safely load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    os.environ.setdefault(k.strip(), v.strip().strip("'\""))

def get_database_uri():
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        return 'mysql+pymysql://root:root@127.0.0.1:3306/voting_system_db'
    if db_url.startswith('mysql+mysqlconnector://'):
        db_url = 'mysql+pymysql://' + db_url[len('mysql+mysqlconnector://'):]
    elif db_url.startswith('mysql://'):
        db_url = 'mysql+pymysql://' + db_url[len('mysql://'):]
    return db_url

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ML_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'ml', 'models')