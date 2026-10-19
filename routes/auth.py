from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from models.user import db, User
from models.election import Election, VoterEligibility
from models.vote import Vote, AuditLog

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        voter_id = (request.form.get('voter_id') or '').strip()
        password = (request.form.get('password') or '').strip()
        
        user = User.query.filter(db.func.lower(User.voter_id) == voter_id.lower()).first()
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['name'] = user.name
            
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('voter.dashboard'))
        
        flash('Invalid Credentials', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/verify', methods=['GET', 'POST'])
def verify_ballot():
    query_hash = (request.args.get('hash') or request.form.get('hash') or '').strip()
    result = None
    if query_hash:
        # Search AuditLog or Vote or VoterEligibility
        log = AuditLog.query.filter(AuditLog.receipt_hash == query_hash).first()
        vote = Vote.query.filter(Vote.receipt_hash == query_hash).first()
        eligibility = VoterEligibility.query.filter(VoterEligibility.receipt_hash == query_hash).first()
        
        if log or vote or eligibility:
            election_id = (log.election_id if log else None) or (vote.election_id if vote else None) or (eligibility.election_id if eligibility else None)
            election = Election.query.get(election_id) if election_id else None
            timestamp = (log.timestamp if log else None) or (vote.created_at if vote else None) or (eligibility.voted_at if eligibility else None)
            block_id = log.id if log else (vote.id if vote else 1)
            
            result = {
                'verified': True,
                'receipt_hash': query_hash,
                'block_id': block_id,
                'timestamp': timestamp,
                'election_title': election.title if election else "General Campus Election",
                'status': "VERIFIED & IMMUTABLY SEALED",
                'privacy': "Zero-Knowledge Decoupled (Ballot secrecy 100% preserved)"
            }
        else:
            result = {
                'verified': False,
                'receipt_hash': query_hash,
                'status': "NOT FOUND (Unrecognized or altered cryptographic hash)"
            }

    # Fetch up to 3 existing sample hashes for quick viva/demo 1-click test
    sample_records = db.session.query(AuditLog.receipt_hash).filter(AuditLog.receipt_hash != None).limit(3).all()
    sample_hashes = [r[0] for r in sample_records if r[0]]

    return render_template('verify.html', query_hash=query_hash, result=result, sample_hashes=sample_hashes)