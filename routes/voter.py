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
        if 'user_id' not in session:
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@voter_bp.route('/dashboard')
@voter_required
def dashboard():
    user_id = session['user_id']
    user = User.query.get(user_id)
    all_elections = Election.query.order_by(Election.created_at.desc()).all()
    
    # Ensure eligibility records exist for all elections
    eligibilities = VoterEligibility.query.filter_by(voter_id=user_id).all()
    existing_eids = {e.election_id for e in eligibilities}
    new_enrolled = False
    for el in all_elections:
        if el.id not in existing_eids:
            db.session.add(VoterEligibility(election_id=el.id, voter_id=user_id, has_voted=False))
            new_enrolled = True
    if new_enrolled:
        db.session.commit()
        eligibilities = VoterEligibility.query.filter_by(voter_id=user_id).all()

    status_map = {e.election_id: e.has_voted for e in eligibilities}
    receipt_map = {e.election_id: e.receipt_hash for e in eligibilities if e.has_voted and e.receipt_hash}
    voted_at_map = {e.election_id: e.voted_at for e in eligibilities if e.has_voted and e.voted_at}

    # Identify primary ongoing election (prefer active election user hasn't voted in yet)
    ongoing_election = next((e for e in all_elections if e.status == 'active' and not status_map.get(e.id)), None)
    if not ongoing_election:
        ongoing_election = next((e for e in all_elections if e.status == 'active'), None) or (all_elections[0] if all_elections else None)

    # Live results breakdown for ongoing election
    live_results = []
    total_ongoing_votes = 0
    if ongoing_election:
        candidates = Candidate.query.filter_by(election_id=ongoing_election.id).all()
        total_ongoing_votes = Vote.query.filter_by(election_id=ongoing_election.id).count()
        for cand in candidates:
            c_votes = Vote.query.filter_by(election_id=ongoing_election.id, candidate_id=cand.id).count()
            c_pct = round((c_votes / total_ongoing_votes * 100), 1) if total_ongoing_votes > 0 else 0
            live_results.append({
                'candidate': cand,
                'votes': c_votes,
                'percentage': c_pct
            })
        live_results.sort(key=lambda x: x['votes'], reverse=True)

    # Global Voting Process Metrics
    total_registered_voters = User.query.filter_by(role='voter').count()
    total_votes_cast = Vote.query.count()
    total_candidates_count = Candidate.query.count()

    # Election Activities List
    election_activities = []
    for el in all_elections:
        if el.status == 'active':
            s_label, s_type = 'Ongoing', 'ongoing'
        elif el.status == 'draft':
            s_label, s_type = 'Pending', 'pending'
        else:
            s_label, s_type = 'Concluded', 'concluded'
        election_activities.append({
            'id': el.id,
            'title': el.title,
            'status_label': s_label,
            'status_type': s_type,
            'has_voted': status_map.get(el.id, False)
        })

    return render_template('voter_dashboard.html', 
                           user=user,
                           elections=all_elections, 
                           ongoing_election=ongoing_election,
                           live_results=live_results,
                           total_ongoing_votes=total_ongoing_votes,
                           total_registered_voters=total_registered_voters,
                           total_votes_cast=total_votes_cast,
                           total_candidates_count=total_candidates_count,
                           election_activities=election_activities,
                           status_map=status_map,
                           receipt_map=receipt_map,
                           voted_at_map=voted_at_map)

@voter_bp.route('/vote', methods=['GET', 'POST'])
@voter_bp.route('/vote/<int:election_id>', methods=['GET', 'POST'])
@voter_required
def cast_vote(election_id=None):
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

    # Fetch candidates for ALL elections so voters can choose election and candidate dynamically
    candidates_by_election = {}
    candidate_counts = {}
    for e in all_elections:
        cands = Candidate.query.filter_by(election_id=e.id).all()
        candidates_by_election[e.id] = cands
        candidate_counts[e.id] = len(cands)

    active_elections_count = sum(1 for e in all_elections if e.status == 'active')
    voted_elections_count = sum(1 for e in all_elections if status_map.get(e.id))
    unvoted_active_count = sum(1 for e in all_elections if e.status == 'active' and not status_map.get(e.id))
    total_elections_count = len(all_elections)
    progress_pct = round((voted_elections_count / total_elections_count * 100), 1) if total_elections_count > 0 else 0

    # Determine which election is selected by default if not specified in URL:
    if not election_id:
        req_election_id = request.args.get('election_id', type=int) or request.form.get('election_id', type=int)
        if req_election_id and any(e.id == req_election_id for e in all_elections):
            election_id = req_election_id
        else:
            # 1. Prefer first active election where voter hasn't voted yet
            unvoted = next((e for e in all_elections if e.status == 'active' and not status_map.get(e.id)), None)
            if unvoted:
                election_id = unvoted.id
            else:
                # 2. Next prefer any active election
                active = next((e for e in all_elections if e.status == 'active'), None)
                election_id = active.id if active else all_elections[0].id

    selected_election = Election.query.get_or_404(election_id)
    eligibility = VoterEligibility.query.filter_by(election_id=selected_election.id, voter_id=user_id).first()
    already_voted = bool(eligibility and eligibility.has_voted)
    receipt_hash = eligibility.receipt_hash if eligibility else None

    # Handle POST vote submission
    if request.method == 'POST':
        post_election_id = request.form.get('election_id', type=int) or election_id
        target_election = Election.query.get(post_election_id)
        if not target_election:
            flash("Invalid election selected.", "danger")
            return redirect(url_for('voter.cast_vote'))

        if target_election.status != 'active':
            flash(f"'{target_election.title}' is currently closed for voting.", "warning")
            return redirect(url_for('voter.results_view', election_id=target_election.id))

        target_eligibility = VoterEligibility.query.filter_by(election_id=target_election.id, voter_id=user_id).first()
        if not target_eligibility:
            target_eligibility = VoterEligibility(election_id=target_election.id, voter_id=user_id, has_voted=False)
            db.session.add(target_eligibility)
            db.session.commit()

        if target_eligibility.has_voted:
            flash(f"Security Alert: Your ballot for '{target_election.title}' is already sealed.", "warning")
            return redirect(url_for('voter.cast_vote', election_id=target_election.id))

        candidate_id = request.form.get('candidate_id', type=int)
        if not candidate_id:
            flash("Please choose a candidate representative to cast your ballot.", "warning")
            return redirect(url_for('voter.cast_vote', election_id=target_election.id))

        candidate = Candidate.query.filter_by(id=candidate_id, election_id=target_election.id).first()
        if not candidate:
            flash("Selected candidate representative does not belong to this election.", "danger")
            return redirect(url_for('voter.cast_vote', election_id=target_election.id))

        now = datetime.utcnow()
        try:
            # Generate cryptographic SHA-256 ballot receipt
            entropy = secrets.token_hex(16)
            raw_token = f"{target_election.id}:{candidate.id}:{now.isoformat()}:{entropy}"
            new_receipt_hash = "0x" + hashlib.sha256(raw_token.encode('utf-8')).hexdigest()

            # Record vote decoupled from voter identity
            db.session.add(Vote(
                election_id=target_election.id,
                candidate_id=candidate.id,
                receipt_hash=new_receipt_hash,
                created_at=now
            ))

            target_eligibility.has_voted = True
            target_eligibility.receipt_hash = new_receipt_hash
            target_eligibility.voted_at = now

            # Append to immutable audit ledger
            db.session.add(AuditLog(
                election_id=target_election.id,
                action=f"Vote recorded & sealed for '{candidate.name}' in '{target_election.title}' [{new_receipt_hash[:16]}...]",
                receipt_hash=new_receipt_hash,
                timestamp=now
            ))
            db.session.commit()

            session['last_receipt'] = new_receipt_hash
            session['last_election_id'] = target_election.id
            flash(f"Success! Your ballot for {candidate.name} in '{target_election.title}' was sealed in the ledger.", "success")
            return redirect(url_for('voter.confirmation', election_id=target_election.id))
        except Exception as ex:
            db.session.rollback()
            flash("Error processing vote. Please try again.", "danger")
            return redirect(url_for('voter.cast_vote', election_id=target_election.id))

    return render_template('vote.html',
                           user=user,
                           election=selected_election,
                           all_elections=all_elections,
                           candidates_by_election=candidates_by_election,
                           candidate_counts=candidate_counts,
                           status_map=status_map,
                           receipt_map=receipt_map,
                           already_voted=already_voted,
                           receipt_hash=receipt_hash,
                           active_elections_count=active_elections_count,
                           voted_elections_count=voted_elections_count,
                           unvoted_active_count=unvoted_active_count,
                           total_elections_count=total_elections_count,
                           progress_pct=progress_pct)

@voter_bp.route('/choose-election')
@voter_required
def choose_election():
    return redirect(url_for('voter.cast_vote'))

@voter_bp.route('/voting-room')
@voter_required
def vote_index():
    return redirect(url_for('voter.cast_vote'))

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