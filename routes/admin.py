import io
import csv
from datetime import datetime, timedelta
from flask import Blueprint, render_template, session, redirect, url_for, Response, flash
from models.user import User, db
from models.election import Election, Candidate, VoterEligibility
from models.vote import Vote, AuditLog
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
    candidate_standings = []
    
    if active_election:
        eligible_count = VoterEligibility.query.filter_by(election_id=active_election.id).count()
        candidates = Candidate.query.filter_by(election_id=active_election.id).all()
        cand_count = len(candidates)
        
        # Calculate live candidate standings
        for cand in candidates:
            c_votes = Vote.query.filter_by(election_id=active_election.id, candidate_id=cand.id).count()
            c_pct = round((c_votes / total_votes * 100), 1) if total_votes > 0 else 0.0
            candidate_standings.append({
                'candidate': cand,
                'votes': c_votes,
                'percentage': c_pct
            })
        candidate_standings.sort(key=lambda x: x['votes'], reverse=True)
        
        # Turnout prediction
        predicted_turnout = turnout_predictor.predict(
            total_eligible=eligible_count or 100, prev_turnout=70.0,
            num_candidates=cand_count or 2, duration_hours=24, prev_participation_rate=0.75
        )
        
        # Anomaly Detection check
        if session.get('simulate_burst', False):
            result = anomaly_detector.analyze_burst(votes_in_1min=28, unique_ips_ratio=0.15, rapid_submissions=25)
            if result.get('flag'):
                anomalies.append(result)
        else:
            recent_window = datetime.utcnow() - timedelta(minutes=1)
            recent_votes = Vote.query.filter(Vote.election_id == active_election.id, Vote.created_at >= recent_window).count()
            result = anomaly_detector.analyze_burst(recent_votes, 0.95, recent_votes)
            if result.get('flag'):
                anomalies.append(result)

    # Fetch recent audit ledger entries
    audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(8).all()
    simulating = session.get('simulate_burst', False)

    return render_template('admin/dashboard.html', 
                           active_elections=active_elections, total_voters=total_voters,
                           total_votes=total_votes, current_turnout=current_turnout,
                           predicted_turnout=predicted_turnout, anomalies=anomalies,
                           candidate_standings=candidate_standings,
                           active_election=active_election,
                           audit_logs=audit_logs,
                           simulating=simulating)

@admin_bp.route('/export/results')
@admin_required
def export_results():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Election Title', 'Candidate Name', 'Position', 'Votes Cast', 'Vote Share (%)'])
    
    active_election = Election.query.filter_by(status='active').first()
    if active_election:
        total = Vote.query.filter_by(election_id=active_election.id).count()
        candidates = Candidate.query.filter_by(election_id=active_election.id).all()
        for cand in candidates:
            c_votes = Vote.query.filter_by(election_id=active_election.id, candidate_id=cand.id).count()
            pct = round((c_votes / total * 100), 2) if total > 0 else 0.0
            writer.writerow([active_election.title, cand.name, cand.position, c_votes, f"{pct}%"])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=votex_election_results.csv"}
    )

@admin_bp.route('/export/audit')
@admin_required
def export_audit():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Log ID', 'Election ID', 'Timestamp (UTC)', 'Action Performed'])
    
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    for log in logs:
        writer.writerow([log.id, log.election_id or 'System', log.timestamp.strftime('%Y-%m-%d %H:%M:%S'), log.action])
    
    output.seek(0)
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=votex_audit_ledger.csv"}
    )

@admin_bp.route('/toggle-simulation', methods=['POST'])
@admin_required
def toggle_simulation():
    session['simulate_burst'] = not session.get('simulate_burst', False)
    if session['simulate_burst']:
        flash("AI Anomaly Stress Test ENABLED: Simulated vote velocity burst active.", "warning")
    else:
        flash("AI Anomaly Stress Test DISABLED: Nominal traffic restored.", "success")
    return redirect(url_for('admin.dashboard'))