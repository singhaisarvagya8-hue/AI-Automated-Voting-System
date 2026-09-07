from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.user import db
from models.election import Election, Candidate, VoterEligibility
from models.vote import Vote, AuditLog

voter_bp = Blueprint('voter', __name__)

def voter_required(f):
    def wrap(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'voter':
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@voter_bp.route('/dashboard')
@voter_required
def dashboard():
    user_id = session['user_id']
    eligibilities = VoterEligibility.query.filter_by(voter_id=user_id).all()
    election_ids = [e.election_id for e in eligibilities]
    
    if election_ids:
        elections = Election.query.filter(Election.id.in_(election_ids), Election.status == 'active').all()
    else:
        elections = []
    status_map = {e.election_id: e.has_voted for e in eligibilities}
    return render_template('voter_dashboard.html', elections=elections, status_map=status_map)

@voter_bp.route('/vote/<int:election_id>', methods=['GET', 'POST'])
@voter_required
def cast_vote(election_id):
    user_id = session['user_id']
    eligibility = VoterEligibility.query.filter_by(election_id=election_id, voter_id=user_id).first()
    
    if not eligibility:
        flash("Not registered for this election.", "danger")
        return redirect(url_for('voter.dashboard'))
        
    if eligibility.has_voted:
        flash("Security Alert: You have already voted.", "warning")
        return redirect(url_for('voter.dashboard'))

    election = Election.query.get_or_404(election_id)

    if request.method == 'POST':
        candidate_id = request.form.get('candidate_id')
        try:
            db.session.add(Vote(election_id=election_id, candidate_id=candidate_id))
            eligibility.has_voted = True
            db.session.add(AuditLog(election_id=election_id, action="Vote recorded"))
            db.session.commit()
            return redirect(url_for('voter.confirmation'))
        except Exception:
            db.session.rollback()
            flash("Error processing vote.", "danger")
            return redirect(url_for('voter.dashboard'))

    candidates = Candidate.query.filter_by(election_id=election_id).all()
    return render_template('vote.html', election=election, candidates=candidates)

@voter_bp.route('/confirmation')
@voter_required
def confirmation():
    return render_template('confirmation.html')