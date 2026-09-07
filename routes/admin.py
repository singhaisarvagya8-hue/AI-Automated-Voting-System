from datetime import datetime, timedelta
from flask import Blueprint, render_template, session, redirect, url_for
from models.user import User
from models.election import Election, Candidate, VoterEligibility
from models.vote import Vote
from ml.turnout_model import TurnoutPredictor
from ml.anomaly_detection import AnomalyDetector

admin_bp = Blueprint('admin', __name__)
turnout_predictor = TurnoutPredictor()
anomaly_detector = AnomalyDetector()

def admin_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@admin_bp.route('/dashboard')
@admin_required
def dashboard():
    active_elections = Election.query.filter_by(status='active').count()
    total_voters = User.query.filter_by(role='voter').count()
    total_votes = Vote.query.count()
    current_turnout = round((total_votes / total_voters * 100), 2) if total_voters > 0 else 0
    
    active_election = Election.query.filter_by(status='active').first()
    predicted_turnout = 0.0
    anomalies = []
    
    if active_election:
        eligible_count = VoterEligibility.query.filter_by(election_id=active_election.id).count()
        cand_count = Candidate.query.filter_by(election_id=active_election.id).count()
        
        predicted_turnout = turnout_predictor.predict(
            total_eligible=eligible_count or 100, prev_turnout=70.0,
            num_candidates=cand_count or 2, duration_hours=24, prev_participation_rate=0.75
        )
        
        recent_window = datetime.utcnow() - timedelta(minutes=1)
        recent_votes = Vote.query.filter(Vote.election_id == active_election.id, Vote.created_at >= recent_window).count()
        result = anomaly_detector.analyze_burst(recent_votes, 0.95, recent_votes)
        if result['flag']:
            anomalies.append(result)

    return render_template('admin/dashboard.html', 
                           active_elections=active_elections, total_voters=total_voters,
                           total_votes=total_votes, current_turnout=current_turnout,
                           predicted_turnout=predicted_turnout, anomalies=anomalies)