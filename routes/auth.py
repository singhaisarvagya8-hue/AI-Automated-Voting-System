from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from models.user import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        voter_id = request.form.get('voter_id')
        password = request.form.get('password')
        
        user = User.query.filter_by(voter_id=voter_id).first()
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