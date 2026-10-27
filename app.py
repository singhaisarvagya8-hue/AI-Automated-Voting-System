import os
from datetime import datetime, timedelta
from flask import Flask, redirect, url_for, session, jsonify, request
from config import Config
from models.user import db, User
from models.election import Election, Candidate, VoterEligibility
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

@app.route('/verify')
def public_verify():
    return redirect(url_for('auth.verify_ballot'))

@app.route('/results')
@app.route('/results/<int:election_id>')
def public_results(election_id=None):
    return redirect(url_for('voter.results_view', election_id=election_id))

@app.route('/create-election')
def public_create_election():
    return redirect(url_for('admin.create_election_section'))

@app.route('/vote')
@app.route('/vote/<int:election_id>')
def public_vote(election_id=None):
    if election_id:
        return redirect(url_for('voter.cast_vote', election_id=election_id))
    return redirect(url_for('voter.choose_election'))

@app.route('/api/search')
def global_search():
    query = (request.args.get('q') or '').strip().lower()
    if not query or len(query) < 1:
        return jsonify({'candidates': [], 'elections': []})
    
    candidates = []
    elections = []
    
    all_cands = Candidate.query.all()
    for c in all_cands:
        el = Election.query.get(c.election_id)
        pos = (c.position or '').lower()
        mf = (c.manifesto or '').lower()
        if query in c.name.lower() or query in pos or query in mf or (el and query in el.title.lower()):
            candidates.append({
                'id': c.id,
                'name': c.name,
                'position': c.position or 'Representative',
                'election_id': c.election_id,
                'election_title': el.title if el else 'Election',
                'vote_url': url_for('voter.cast_vote', election_id=c.election_id),
                'results_url': url_for('voter.results_view', election_id=c.election_id)
            })
            
    all_elecs = Election.query.all()
    for e in all_elecs:
        desc = (e.description or '').lower()
        if query in e.title.lower() or query in desc:
            elections.append({
                'id': e.id,
                'title': e.title,
                'status': e.status,
                'vote_url': url_for('voter.cast_vote', election_id=e.id),
                'results_url': url_for('voter.results_view', election_id=e.id)
            })
            
    return jsonify({
        'query': query,
        'candidates': candidates[:6],
        'elections': elections[:4]
    })

@app.context_processor
def inject_announcements():
    try:
        from services.announcements import get_recent_announcements, get_winner_announcements
        announcements = get_recent_announcements(limit=8)
        winners = get_winner_announcements(limit=5)
        unread_count = min(len(announcements), 5)
        return {
            'global_announcements': announcements,
            'global_winners': winners,
            'global_unread_notifications_count': unread_count
        }
    except Exception as e:
        return {
            'global_announcements': [],
            'global_winners': [],
            'global_unread_notifications_count': 0
        }

def init_app_state():
    with app.app_context():
        try:
            db.create_all()
            for table, col, defn in [
                ('voter_eligibility', 'receipt_hash', 'VARCHAR(66) NULL'),
                ('voter_eligibility', 'voted_at', 'DATETIME NULL'),
                ('votes', 'receipt_hash', 'VARCHAR(66) NULL'),
                ('audit_logs', 'receipt_hash', 'VARCHAR(66) NULL')
            ]:
                try:
                    exists = db.session.execute(db.text(
                        f"SELECT count(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table}' AND COLUMN_NAME = '{col}'"
                    )).scalar()
                    if not exists:
                        db.session.execute(db.text(f"ALTER TABLE {table} ADD COLUMN {col} {defn}"))
                        db.session.commit()
                except Exception:
                    db.session.rollback()
            
            # Auto-seed initial demo accounts and election if database is brand new (e.g. cloud/serverless deploy)
            try:
                if User.query.count() == 0:
                    admin_user = User(
                        name="System Administrator",
                        email="admin@college.edu",
                        voter_id="ADMIN001",
                        role="admin",
                        department="Administration",
                        year=0
                    )
                    admin_user.set_password("password123")
                    db.session.add(admin_user)

                    voter1 = User(
                        name="Rahul Sharma",
                        email="rahul.s@college.edu",
                        voter_id="CS202601",
                        role="voter",
                        department="Computer Science",
                        year=3
                    )
                    voter1.set_password("password123")
                    db.session.add(voter1)

                    voter2 = User(
                        name="Sneha Patel",
                        email="sneha.p@college.edu",
                        voter_id="CS202602",
                        role="voter",
                        department="Computer Science",
                        year=3
                    )
                    voter2.set_password("password123")
                    db.session.add(voter2)
                    db.session.commit()

                    now = datetime.utcnow()
                    el = Election(
                        title="Student Council Election 2026",
                        description="Official campus-wide election for Student Council Executive Representatives.",
                        start_time=now,
                        end_time=now + timedelta(hours=48),
                        status="active",
                        created_at=now
                    )
                    db.session.add(el)
                    db.session.flush()

                    c1 = Candidate(election_id=el.id, name="Aarav Sharma", position="Executive President", manifesto="Committed to 24/7 technical infrastructure, research grants, and student innovation.")
                    c2 = Candidate(election_id=el.id, name="Priya Nair", position="Executive President", manifesto="Focusing on student wellness subsidies, quality mess audits, and mental health counseling.")
                    db.session.add_all([c1, c2])

                    db.session.add(VoterEligibility(election_id=el.id, voter_id=voter1.id, has_voted=False))
                    db.session.add(VoterEligibility(election_id=el.id, voter_id=voter2.id, has_voted=False))
                    db.session.commit()
                    print(" * Auto-seeded initial demo users and election.")
            except Exception as e:
                db.session.rollback()
                print(f" * Seed data init note: {e}")

            # Sync announcements for existing contests
            try:
                from services.announcements import sync_all_announcements
                sync_all_announcements()
            except Exception as e:
                print(f" * Announcement sync note: {e}")

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