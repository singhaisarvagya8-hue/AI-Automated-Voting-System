import os
from datetime import datetime
from models.user import db
from models.election import Election, Candidate, Announcement
from models.vote import Vote

def publish_election_added_announcement(election, candidate_count=None):
    """Publish an announcement when a new election is added."""
    if candidate_count is None:
        candidate_count = Candidate.query.filter_by(election_id=election.id).count()
    
    existing = Announcement.query.filter_by(
        election_id=election.id,
        announcement_type='election_added'
    ).first()
    
    if not existing:
        ann = Announcement(
            election_id=election.id,
            title=f"New Election Added: {election.title}",
            message=f"The Election Commission has officially launched the voting chamber for '{election.title}'. {candidate_count} candidate representative{'s' if candidate_count != 1 else ''} have been registered on the ballot. Eligible voters may cast their confidential single vote now.",
            announcement_type='election_added',
            badge_text='New Election',
            created_at=election.created_at or datetime.utcnow()
        )
        db.session.add(ann)
        try:
            db.session.commit()
            return ann
        except Exception:
            db.session.rollback()
            return None
    return existing

def publish_winner_announcement(election):
    """Compute winner and publish official winner declaration announcement."""
    candidates = Candidate.query.filter_by(election_id=election.id).all()
    if not candidates:
        return None
        
    total_votes = Vote.query.filter_by(election_id=election.id).count()
    
    standings = []
    for c in candidates:
        votes = Vote.query.filter_by(election_id=election.id, candidate_id=c.id).count()
        pct = round((votes / total_votes * 100), 1) if total_votes > 0 else 0.0
        standings.append({
            'candidate': c,
            'votes': votes,
            'percentage': pct
        })
    standings.sort(key=lambda x: x['votes'], reverse=True)
    
    winner_info = standings[0]
    winner = winner_info['candidate']
    winner_votes = winner_info['votes']
    winner_pct = winner_info['percentage']
    
    existing = Announcement.query.filter_by(
        election_id=election.id,
        announcement_type='winner_declared'
    ).first()
    
    if existing:
        existing.winner_name = winner.name
        existing.winner_position = winner.position
        existing.winner_votes = winner_votes
        existing.winner_percentage = winner_pct
        existing.title = f"Official Winner Announced: {winner.name} ({election.title})"
        existing.message = f"{winner.name} ({winner.position}) has officially emerged victorious in '{election.title}' with {winner_votes} votes ({winner_pct}% share)! The ballot ledger is cryptographically sealed and verified."
        existing.created_at = datetime.utcnow()
        try:
            db.session.commit()
            return existing
        except Exception:
            db.session.rollback()
            return None
    else:
        ann = Announcement(
            election_id=election.id,
            title=f"Official Winner Announced: {winner.name} ({election.title})",
            message=f"{winner.name} ({winner.position}) has officially emerged victorious in '{election.title}' with {winner_votes} votes ({winner_pct}% share)! The ballot ledger is cryptographically sealed and verified.",
            announcement_type='winner_declared',
            winner_name=winner.name,
            winner_position=winner.position,
            winner_votes=winner_votes,
            winner_percentage=winner_pct,
            badge_text='Winner Declared',
            created_at=datetime.utcnow()
        )
        db.session.add(ann)
        try:
            db.session.commit()
            return ann
        except Exception:
            db.session.rollback()
            return None

def get_recent_announcements(limit=10):
    """Retrieve recent announcements sorted by created_at desc."""
    return Announcement.query.order_by(Announcement.created_at.desc()).limit(limit).all()

def get_winner_announcements(limit=6):
    """Retrieve winner announcements."""
    return Announcement.query.filter_by(announcement_type='winner_declared').order_by(Announcement.created_at.desc()).limit(limit).all()

def sync_all_announcements():
    """Ensure all existing elections have election_added and closed/declared elections have winner_declared."""
    try:
        elections = Election.query.all()
        for el in elections:
            c_count = Candidate.query.filter_by(election_id=el.id).count()
            publish_election_added_announcement(el, c_count)
            if el.status == 'closed':
                publish_winner_announcement(el)
    except Exception as e:
        print(f"Announcement sync notice: {e}")
