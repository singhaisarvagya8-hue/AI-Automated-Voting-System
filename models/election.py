from datetime import datetime
from models.user import db

class Election(db.Model):
    __tablename__ = 'elections'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    start_time = db.Column(db.DateTime, nullable=False)
    end_time = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='draft')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    candidates = db.relationship('Candidate', backref='election', lazy=True, cascade="all, delete-orphan")
    eligibilities = db.relationship('VoterEligibility', backref='election', lazy=True, cascade="all, delete-orphan")
    votes = db.relationship('Vote', backref='election', lazy=True, cascade="all, delete-orphan")
    announcements = db.relationship('Announcement', backref='election', lazy=True, cascade="all, delete-orphan")

class Candidate(db.Model):
    __tablename__ = 'candidates'
    
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    position = db.Column(db.String(100), nullable=False)
    manifesto = db.Column(db.Text, nullable=True)
    photo = db.Column(db.String(255), nullable=True, default='default.jpg')

class VoterEligibility(db.Model):
    __tablename__ = 'voter_eligibility'
    
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=False)
    voter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    has_voted = db.Column(db.Boolean, default=False, nullable=False)
    receipt_hash = db.Column(db.String(66), nullable=True)
    voted_at = db.Column(db.DateTime, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('election_id', 'voter_id', name='unique_voter_per_election'),
    )

class Announcement(db.Model):
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    election_id = db.Column(db.Integer, db.ForeignKey('elections.id'), nullable=True)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    announcement_type = db.Column(db.String(50), default='election_added')  # 'election_added', 'winner_declared', 'status_update'
    winner_name = db.Column(db.String(100), nullable=True)
    winner_position = db.Column(db.String(100), nullable=True)
    winner_votes = db.Column(db.Integer, default=0)
    winner_percentage = db.Column(db.Float, default=0.0)
    badge_text = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
