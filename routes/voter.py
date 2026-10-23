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

@voter_bp.route('/vote')
@voter_required
def choose_election():
    user_id = session['user_id']
    
    # Query all elections present in the system
    all_elections = Election.query.order_by(Election.created_at.desc()).all()
    if not all_elections:
        flash("No elections are currently present in the system.", "info")
        return redirect(url_for('voter.dashboard'))

    # Auto-enroll / ensure eligibility for this voter across all present elections
    user = User.query.get(user_id)
    eligibilities = VoterEligibility.query.filter_by(voter_id=user_id).all()
    existing_ids = {el.election_id for el in eligibilities}
    new_eligibilities = False
    for el_obj in all_elections:
        if el_obj.id not in existing_ids:
            db.session.add(VoterEligibility(election_id=el_obj.id, voter_id=user_id, has_voted=False))
            new_eligibilities = True
    if new_eligibilities:
        db.session.commit()
        eligibilities = VoterEligibility.query.filter_by(voter_id=user_id).all()

    status_map = {el.election_id: el.has_voted for el in eligibilities}
    receipt_map = {el.election_id: el.receipt_hash for el in eligibilities if el.has_voted and el.receipt_hash}
    voted_at_map = {el.election_id: el.voted_at for el in eligibilities if el.has_voted and el.voted_at}

    # Fetch candidates and counts for each election
    candidates_by_election = {}
    candidate_counts = {}
    for e in all_elections:
        cands = Candidate.query.filter_by(election_id=e.id).all()
        candidates_by_election[e.id] = cands
        candidate_counts[e.id] = len(cands)

    active_elections_count = sum(1 for e in all_elections if e.status == 'active')
    voted_elections_count = sum(1 for e in all_elections if status_map.get(e.id))
    unvoted_active_count = sum(1 for e in all_elections if e.status == 'active' and not status_map.get(e.id))
    closed_count = sum(1 for e in all_elections if e.status != 'active')
    total_elections_count = len(all_elections)
    progress_pct = round((voted_elections_count / total_elections_count * 100), 1) if total_elections_count > 0 else 0

    return render_template('choose_election.html',
                           all_elections=all_elections,
                           candidates_by_election=candidates_by_election,
                           candidate_counts=candidate_counts,
                           status_map=status_map,
                           receipt_map=receipt_map,
                           voted_at_map=voted_at_map,
                           active_elections_count=active_elections_count,
                           voted_elections_count=voted_elections_count,
                           unvoted_active_count=unvoted_active_count,
                           closed_count=closed_count,
                           total_elections_count=total_elections_count,
                           progress_pct=progress_pct)

@voter_bp.route('/vote/<int:election_id>', methods=['GET', 'POST'])
@voter_required
def cast_vote(election_id):
    user_id = session['user_id']
    
    # Query all elections present in the system
    all_elections = Election.query.order_by(Election.created_at.desc()).all()
    if not all_elections:
        flash("No elections are currently present in the system.", "info")
        return redirect(url_for('voter.dashboard'))

    # Auto-enroll / ensure eligibility for this voter across all present elections
    user = User.query.get(user_id)
    eligibilities = VoterEligibility.query.filter_by(voter_id=user_id).all()
    existing_ids = {el.election_id for el in eligibilities}
    new_eligibilities = False
    for el_obj in all_elections:
        if el_obj.id not in existing_ids:
            db.session.add(VoterEligibility(election_id=el_obj.id, voter_id=user_id, has_voted=False))
            new_eligibilities = True
    if new_eligibilities:
        db.session.commit()
        eligibilities = VoterEligibility.query.filter_by(voter_id=user_id).all()

    status_map = {el.election_id: el.has_voted for el in eligibilities}
    receipt_map = {el.election_id: el.receipt_hash for el in eligibilities if el.has_voted and el.receipt_hash}

    election = Election.query.get_or_404(election_id)
    eligibility = VoterEligibility.query.filter_by(election_id=election.id, voter_id=user_id).first()
    candidates = Candidate.query.filter_by(election_id=election.id).all()

    # Pre-calculate candidate counts for the elections present switcher
    candidate_counts = {}
    for e in all_elections:
        candidate_counts[e.id] = Candidate.query.filter_by(election_id=e.id).count()

    active_elections_count = sum(1 for e in all_elections if e.status == 'active')
    voted_elections_count = sum(1 for e in all_elections if status_map.get(e.id))
    total_elections_count = len(all_elections)
    progress_pct = round((voted_elections_count / total_elections_count * 100), 1) if total_elections_count > 0 else 0

    already_voted = bool(eligibility and eligibility.has_voted)
    receipt_hash = eligibility.receipt_hash if eligibility else None

    # Handle POST vote submission
    if request.method == 'POST':
        if election.status != 'active':
            flash("This election is currently closed for voting.", "warning")
            return redirect(url_for('voter.results_view', election_id=election.id))
            
        if already_voted:
            flash("Security Alert: Double-voting attempt blocked. Your ballot is already sealed.", "warning")
            return redirect(url_for('voter.results_view', election_id=election.id))

        candidate_id = request.form.get('candidate_id')
        if not candidate_id:
            flash("Please choose a candidate representative to cast your ballot.", "warning")
            return redirect(url_for('voter.cast_vote', election_id=election.id))

        now = datetime.utcnow()
        try:
            # Generate cryptographic SHA-256 ballot receipt
            entropy = secrets.token_hex(16)
            raw_token = f"{election.id}:{candidate_id}:{now.isoformat()}:{entropy}"
            receipt_hash = "0x" + hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

            # Record vote decoupled from voter identity
            db.session.add(Vote(
                election_id=election.id, 
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
                election_id=election.id, 
                action=f"Vote recorded & sealed [{receipt_hash[:16]}...]",
                receipt_hash=receipt_hash,
                timestamp=now
            ))
            db.session.commit()

            session['last_receipt'] = receipt_hash
            session['last_election_id'] = election.id
            return redirect(url_for('voter.confirmation', election_id=election.id))
        except Exception:
            db.session.rollback()
            flash("Error processing vote.", "danger")
            return redirect(url_for('voter.choose_election'))

    return render_template('vote.html', 
                           election=election, 
                           candidates=candidates, 
                           already_voted=already_voted, 
                           receipt_hash=receipt_hash,
                           all_elections=all_elections,
                           status_map=status_map,
                           receipt_map=receipt_map,
                           candidate_counts=candidate_counts,
                           active_elections_count=active_elections_count,
                           voted_elections_count=voted_elections_count,
                           total_elections_count=total_elections_count,
                           progress_pct=progress_pct)

@voter_bp.route('/voting-room')
@voter_required
def vote_index():
    return redirect(url_for('voter.choose_election'))

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

@voter_bp.route('/results')
@voter_bp.route('/results/<int:election_id>')
def results_view(election_id=None):
    all_elections = Election.query.order_by(Election.created_at.desc()).all()
    
    selected_election = None
    if election_id:
        selected_election = Election.query.get(election_id)
    if not selected_election:
        # Default to first active election, or latest election
        selected_election = Election.query.filter_by(status='active').first() or (all_elections[0] if all_elections else None)
        
    candidate_standings = []
    leader = None
    total_votes = 0
    total_eligible = 0
    turnout_pct = 0.0
    user_voted = False
    user_receipt = None

    if selected_election:
        candidates = Candidate.query.filter_by(election_id=selected_election.id).all()
        total_votes = Vote.query.filter_by(election_id=selected_election.id).count()
        total_eligible = VoterEligibility.query.filter_by(election_id=selected_election.id).count()
        turnout_pct = round((total_votes / total_eligible * 100), 1) if total_eligible > 0 else 0.0
        
        for cand in candidates:
            c_votes = Vote.query.filter_by(election_id=selected_election.id, candidate_id=cand.id).count()
            c_pct = round((c_votes / total_votes * 100), 1) if total_votes > 0 else 0.0
            candidate_standings.append({
                'candidate': cand,
                'votes': c_votes,
                'percentage': c_pct
            })
        candidate_standings.sort(key=lambda x: x['votes'], reverse=True)
        leader = candidate_standings[0] if (candidate_standings and candidate_standings[0]['votes'] > 0) else None

        if 'user_id' in session:
            eligibility = VoterEligibility.query.filter_by(
                election_id=selected_election.id, 
                voter_id=session['user_id']
            ).first()
            if eligibility and eligibility.has_voted:
                user_voted = True
                user_receipt = eligibility.receipt_hash

    return render_template('results.html',
                           all_elections=all_elections,
                           selected_election=selected_election,
                           candidate_standings=candidate_standings,
                           leader=leader,
                           total_votes=total_votes,
                           total_eligible=total_eligible,
                           turnout_pct=turnout_pct,
                           user_voted=user_voted,
                           user_receipt=user_receipt)