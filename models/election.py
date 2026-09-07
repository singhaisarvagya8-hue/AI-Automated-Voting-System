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

    __table_args__ = (
        db.UniqueConstraint('election_id', 'voter_id', name='unique_voter_per_election'),
    )