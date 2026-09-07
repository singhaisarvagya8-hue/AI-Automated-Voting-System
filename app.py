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

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    port = int(os.environ.get('PORT', 5001))
    print(f"\n==========================================")
    print(f" * Voting System running at: http://127.0.0.1:{port}")
    print(f"==========================================\n")
    app.run(debug=True, port=port)