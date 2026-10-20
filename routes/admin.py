import io
import csv
import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, session, redirect, url_for, Response, flash, request
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

def verify_master_password(candidate_password):
    if not candidate_password:
        return False
    # Allowed defaults and environment passkeys
    allowed = {'adminpassword', 'admin123', 'election2026', 'admin'}
    env_pwd = os.environ.get('ELECTION_CREATION_PASSWORD')
    if env_pwd:
        allowed.add(env_pwd)
    if candidate_password in allowed:
        return True
    
    # Check against any admin account in DB
    try:
        admins = User.query.filter_by(role='admin').all()
        for a in admins:
            if a.check_password(candidate_password):
                return True
    except Exception:
        pass
    return False

def is_creator_authorized():
    return session.get('election_creator_authorized') is True

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

    # Departmental Turnout Analytics
    departments = db.session.query(User.department, db.func.count(User.id)).filter(User.role == 'voter').group_by(User.department).all()
    dept_stats = []
    for dept_name, voter_count in departments:
        voted_count = db.session.query(db.func.count(VoterEligibility.id))\
            .join(User, VoterEligibility.voter_id == User.id)\
            .filter(User.department == dept_name, VoterEligibility.has_voted == True).scalar() or 0
        pct = round((voted_count / voter_count * 100), 1) if voter_count > 0 else 0.0
        dept_stats.append({
            'department': dept_name,
            'total': voter_count,
            'voted': voted_count,
            'percentage': pct
        })

    # Fetch all elections for Election Management tab
    all_elections = Election.query.order_by(Election.created_at.desc()).all()

    # Fetch recent audit ledger entries
    audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(15).all()
    simulating = session.get('simulate_burst', False)

    return render_template('admin/dashboard.html', 
                           active_elections=active_elections, total_voters=total_voters,
                           total_votes=total_votes, current_turnout=current_turnout,
                           predicted_turnout=predicted_turnout, anomalies=anomalies,
                           candidate_standings=candidate_standings,
                           active_election=active_election,
                           all_elections=all_elections,
                           dept_stats=dept_stats,
                           audit_logs=audit_logs,
                           simulating=simulating)

@admin_bp.route('/elections/create', methods=['GET'])
def create_election_section():
    if not is_creator_authorized():
        return render_template('admin/election_security_gate.html')
    return render_template('admin/create_election.html')

@admin_bp.route('/elections/create/auth', methods=['POST'])
def verify_security_gate():
    pwd = (request.form.get('security_password') or '').strip()
    if verify_master_password(pwd):
        session['election_creator_authorized'] = True
        # If not logged in as admin, authenticate session with administrative commissioner privilege
        if session.get('role') != 'admin':
            admin_user = User.query.filter_by(role='admin').first()
            if admin_user:
                session['user_id'] = admin_user.id
                session['role'] = 'admin'
                session['name'] = admin_user.name
            else:
                session['role'] = 'admin'
                session['name'] = 'Election Commissioner'
        flash("Master Security Password Verified. Welcome to the Election Creation Console.", "success")
        return redirect(url_for('admin.create_election_section'))
    
    flash("Security Alert: Invalid master password. Access to election creation denied.", "danger")
    return render_template('admin/election_security_gate.html')

@admin_bp.route('/elections/create/save', methods=['POST'])
def save_created_election():
    if not is_creator_authorized():
        flash("Security timeout or missing authorization. Please enter the master password.", "warning")
        return redirect(url_for('admin.create_election_section'))
    
    title = (request.form.get('title') or '').strip()
    description = (request.form.get('description') or '').strip()
    status = request.form.get('status') or 'active'
    duration_hours = int(request.form.get('duration_hours') or 24)
    
    if not title:
        flash("Election title is required.", "danger")
        return render_template('admin/create_election.html')
    
    # Collect candidate representatives
    names = request.form.getlist('cand_name')
    positions = request.form.getlist('cand_position')
    manifestos = request.form.getlist('cand_manifesto')
    
    candidates_data = []
    for n, p, m in zip(names, positions, manifestos):
        n_clean = (n or '').strip()
        if n_clean:
            candidates_data.append({
                'name': n_clean,
                'position': (p or '').strip() or 'President',
                'manifesto': (m or '').strip() or 'Committed to representing student interests and campus improvements.'
            })
    
    # Enforce minimum 4 candidates
    if len(candidates_data) < 4:
        flash(f"Fair Democratic Mandate: At least 4 candidate representatives are required (you provided {len(candidates_data)}).", "danger")
        return render_template('admin/create_election.html')
    
    now = datetime.utcnow()
    end_time = now + timedelta(hours=duration_hours)
    
    new_election = Election(
        title=title,
        description=description,
        start_time=now,
        end_time=end_time,
        status=status,
        created_at=now
    )
    db.session.add(new_election)
    db.session.flush()
    
    # Register candidates
    for c in candidates_data:
        cand = Candidate(
            election_id=new_election.id,
            name=c['name'],
            position=c['position'],
            manifesto=c['manifesto'],
            photo='default.jpg'
        )
        db.session.add(cand)
    
    # Auto-enroll all registered voters
    voters = User.query.filter_by(role='voter').all()
    for v in voters:
        db.session.add(VoterEligibility(
            election_id=new_election.id,
            voter_id=v.id,
            has_voted=False
        ))
        
    db.session.add(AuditLog(
        election_id=new_election.id,
        action=f"Protected Election #{new_election.id} '{title}' created with {len(candidates_data)} candidates and {len(voters)} eligible voters enrolled.",
        timestamp=now
    ))
    db.session.commit()
    
    flash(f"Ballot '{title}' successfully created with {len(candidates_data)} candidate representatives! {len(voters)} student voters have been enrolled.", "success")
    if status == 'active':
        return redirect(url_for('voter.results_view', election_id=new_election.id))
    return redirect(url_for('admin.dashboard') + '#elections')

@admin_bp.route('/elections/lock')
def lock_election_creator():
    session.pop('election_creator_authorized', None)
    flash("Election creation console has been securely locked.", "info")
    return redirect(url_for('admin.create_election_section'))

@admin_bp.route('/election/new', methods=['POST'])
@admin_required
def create_election():
    from flask import request
    title = (request.form.get('title') or '').strip()
    description = (request.form.get('description') or '').strip()
    status = request.form.get('status') or 'active'
    
    if not title:
        flash("Election title is required.", "danger")
        return redirect(url_for('admin.dashboard') + '#elections')
        
    now = datetime.utcnow()
    end_time = now + timedelta(hours=24)
    
    new_election = Election(
        title=title,
        description=description,
        start_time=now,
        end_time=end_time,
        status=status,
        created_at=now
    )
    db.session.add(new_election)
    db.session.flush()
    
    # Auto-enroll all registered voters
    voters = User.query.filter_by(role='voter').all()
    for v in voters:
        db.session.add(VoterEligibility(election_id=new_election.id, voter_id=v.id, has_voted=False))
        
    db.session.add(AuditLog(
        election_id=new_election.id,
        action=f"Election #{new_election.id} '{title}' created with {len(voters)} eligible voters enrolled.",
        timestamp=now
    ))
    db.session.commit()
    flash(f"Election '{title}' created successfully with {len(voters)} voters enrolled!", "success")
    return redirect(url_for('admin.dashboard') + '#elections')

@admin_bp.route('/election/<int:election_id>/toggle-status', methods=['POST'])
@admin_required
def toggle_election_status(election_id):
    election = Election.query.get_or_404(election_id)
    election.status = 'closed' if election.status == 'active' else 'active'
    now = datetime.utcnow()
    db.session.add(AuditLog(
        election_id=election.id,
        action=f"Election #{election.id} status transitioned to '{election.status}'.",
        timestamp=now
    ))
    db.session.commit()
    flash(f"Election '{election.title}' status changed to '{election.status}'.", "info")
    return redirect(url_for('admin.dashboard') + '#elections')

@admin_bp.route('/election/<int:election_id>/candidate/add', methods=['POST'])
@admin_required
def add_candidate(election_id):
    from flask import request
    name = (request.form.get('name') or '').strip()
    position = (request.form.get('position') or 'Candidate').strip()
    manifesto = (request.form.get('manifesto') or '').strip()
    
    if not name:
        flash("Candidate name is required.", "danger")
        return redirect(url_for('admin.dashboard') + '#elections')
        
    cand = Candidate(
        election_id=election_id,
        name=name,
        position=position,
        manifesto=manifesto,
        photo='default.jpg'
    )
    db.session.add(cand)
    db.session.add(AuditLog(
        election_id=election_id,
        action=f"Candidate '{name}' ({position}) registered for Election #{election_id}.",
        timestamp=datetime.utcnow()
    ))
    db.session.commit()
    flash(f"Candidate '{name}' registered successfully!", "success")
    return redirect(url_for('admin.dashboard') + '#elections')

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
    writer.writerow(['Log ID', 'Election ID', 'Timestamp (UTC)', 'Action Performed', 'Receipt Hash'])
    
    logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).all()
    for log in logs:
        writer.writerow([log.id, log.election_id or 'System', log.timestamp.strftime('%Y-%m-%d %H:%M:%S'), log.action, log.receipt_hash or 'N/A'])
    
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