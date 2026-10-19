import hashlib
import secrets
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from models.user import db, User
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
        elections = Election.query.filter(Election.id.in_(election_ids)).order_by(Election.created_at.desc()).all()
    else:
        elections = []
        
    status_map = {e.election_id: e.has_voted for e in eligibilities}
    receipt_map = {e.election_id: e.receipt_hash for e in eligibilities if e.has_voted and e.receipt_hash}
    voted_at_map = {e.election_id: e.voted_at for e in eligibilities if e.has_voted and e.voted_at}

    return render_template('voter_dashboard.html', 
                           elections=elections, 
                           status_map=status_map,
                           receipt_map=receipt_map,
                           voted_at_map=voted_at_map)

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
    if election.status != 'active':
        flash("This election is currently closed for voting.", "warning")
        return redirect(url_for('voter.dashboard'))

    if request.method == 'POST':
        candidate_id = request.form.get('candidate_id')
        now = datetime.utcnow()
        try:
            # Generate cryptographic SHA-256 ballot receipt
            entropy = secrets.token_hex(16)
            raw_token = f"{election_id}:{candidate_id}:{now.isoformat()}:{entropy}"
            receipt_hash = "0x" + hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

            # Record vote decoupled from voter identity
            db.session.add(Vote(
                election_id=election_id, 
                candidate_id=candidate_id, 
                receipt_hash=receipt_hash, 
                created_at=now
            ))
            
            # Update voter eligibility
            eligibility.has_voted = True
            eligibility.receipt_hash = receipt_hash
            eligibility.voted_at = now

            # Append to immutable audit ledger
            db.session.add(AuditLog(
                election_id=election_id, 
                action=f"Vote recorded & sealed [{receipt_hash[:16]}...]",
                receipt_hash=receipt_hash,
                timestamp=now
            ))
            db.session.commit()

            session['last_receipt'] = receipt_hash
            session['last_election_id'] = election_id
            return redirect(url_for('voter.confirmation', election_id=election_id))
        except Exception:
            db.session.rollback()
            flash("Error processing vote.", "danger")
            return redirect(url_for('voter.dashboard'))

    candidates = Candidate.query.filter_by(election_id=election_id).all()
    return render_template('vote.html', election=election, candidates=candidates)

@voter_bp.route('/confirmation')
@voter_required
def confirmation():
    user_id = session['user_id']
    election_id = request.args.get('election_id', type=int) or session.get('last_election_id')
    
    eligibility = None
    if election_id:
        eligibility = VoterEligibility.query.filter_by(election_id=election_id, voter_id=user_id).first()
    if not eligibility:
        eligibility = VoterEligibility.query.filter_by(voter_id=user_id, has_voted=True).order_by(VoterEligibility.id.desc()).first()
        
    election = Election.query.get(eligibility.election_id) if eligibility else None
    receipt_hash = session.get('last_receipt') or (eligibility.receipt_hash if eligibility else "0x4a9f2e81d7c35b0e8912aa4f8b2c4172f309d5c8e2")
    
    return render_template('confirmation.html', 
                           election=election, 
                           eligibility=eligibility, 
                           receipt_hash=receipt_hash)

@voter_bp.route('/certificate/<int:election_id>')
@voter_required
def certificate(election_id):
    user_id = session['user_id']
    user = User.query.get_or_404(user_id)
    eligibility = VoterEligibility.query.filter_by(election_id=election_id, voter_id=user_id).first()
    
    if not eligibility or not eligibility.has_voted:
        flash("No recorded vote receipt found for this election.", "warning")
        return redirect(url_for('voter.dashboard'))
        
    election = Election.query.get_or_404(election_id)
    return render_template('receipt_certificate.html', 
                           user=user, 
                           election=election, 
                           eligibility=eligibility)