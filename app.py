import os
from flask import Flask, redirect, url_for, session
from config import Config
from models.user import db
from routes.auth import auth_bp
from routes.voter import voter_bp
from routes.admin import admin_bp

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(voter_bp, url_prefix='/voter')
app.register_blueprint(admin_bp, url_prefix='/admin')

@app.route('/')
def index():
    if 'user_id' in session:
        if session.get('role') == 'admin':
            return redirect(url_for('admin.dashboard'))
        return redirect(url_for('voter.dashboard'))
    return redirect(url_for('auth.login'))

def init_app_state():
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f" * Database init note: {e}")
    
    # Auto-train ML models if missing
    models_dir = os.path.join(os.path.dirname(__file__), 'ml', 'models')
    turnout_path = os.path.join(models_dir, 'turnout_model.pkl')
    anomaly_path = os.path.join(models_dir, 'anomaly_model.pkl')
    if not os.path.exists(turnout_path) or not os.path.exists(anomaly_path):
        try:
            from ml.train_models import train_turnout_model, train_anomaly_model
            train_turnout_model()
            train_anomaly_model()
            print(" * Initialized ML models successfully.")
        except Exception as e:
            print(f" * Warning: ML model auto-init skipped: {e}")

# Run initialization for both direct and WSGI (Gunicorn) execution
init_app_state()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    print(f"\n==========================================")
    print(f" * Votex.ai running at: http://127.0.0.1:{port}")
    print(f"==========================================\n")
    app.run(debug=True, port=port)