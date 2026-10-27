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
    if db_url:
        if db_url.startswith('mysql+mysqlconnector://'):
            return 'mysql+pymysql://' + db_url[len('mysql+mysqlconnector://'):]
        if db_url.startswith('mysql://'):
            return 'mysql+pymysql://' + db_url[len('mysql://'):]
        if db_url.startswith('postgres://'):
            return 'postgresql+psycopg2://' + db_url[len('postgres://'):]
        return db_url

    # Check if running in a serverless cloud environment (Netlify, Vercel, AWS Lambda)
    is_serverless = os.environ.get('NETLIFY') or os.environ.get('AWS_LAMBDA_FUNCTION_NAME') or os.environ.get('VERCEL')
    if is_serverless:
        # SQLite database in writable /tmp directory
        return 'sqlite:////tmp/voting_system.db'

    # Check if local MySQL port 3306 is responsive
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect(('127.0.0.1', 3306))
        s.close()
        return 'mysql+pymysql://root:root@127.0.0.1:3306/voting_system_db'
    except Exception:
        # Fall back to local SQLite file if MySQL server is not running
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return f'sqlite:///{os.path.join(base_dir, "voting_system.db")}'

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'super-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    ML_MODEL_PATH = os.path.join(os.path.dirname(__file__), 'ml', 'models')