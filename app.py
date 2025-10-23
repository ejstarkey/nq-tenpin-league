"""
NQ Tenpin Bowling League Attendance Tracking System
Flask Application - Port 2019
Version 1.0
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import csv
import io
import requests
from functools import wraps
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'nq-tenpin-secure-key-2025')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///nq_tenpin.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=2)

# Email configuration for Microsoft 365
app.config['MAIL_SERVER'] = 'smtp.office365.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'atherton@nqtenpin.com.au'
app.config['MAIL_PASSWORD'] = 'nmmgfdglmwvjrsdy'
app.config['ADMIN_EMAILS'] = ['atherton_bookings@nqtenpin.com.au']  # Add staff emails

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                   filename='nq_tenpin.log')

# ============================================
# DATABASE MODELS
# ============================================

class User(UserMixin, db.Model):
    """Staff user model"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255))
    role = db.Column(db.String(20), default='staff')  # admin or staff
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    
    # Audit trail relationship
    audit_logs = db.relationship('AuditLog', backref='user', lazy='dynamic')

class AuditLog(db.Model):
    """Audit trail for all system actions"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    action = db.Column(db.String(100))
    details = db.Column(db.Text)
    ip_address = db.Column(db.String(50))

class League(db.Model):
    """League model"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    finish_date = db.Column(db.Date, nullable=False)
    social_fee = db.Column(db.Float, default=0)
    bowling_fee = db.Column(db.Float, default=0)
    has_fines = db.Column(db.Boolean, default=False)
    fine_amount = db.Column(db.Float, default=0)
    league_type = db.Column(db.String(20))  # singles or teams
    players_per_team = db.Column(db.Integer)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    teams = db.relationship('Team', backref='league', lazy='dynamic', cascade='all, delete-orphan')
    bowler_leagues = db.relationship('BowlerLeague', backref='league', lazy='dynamic', cascade='all, delete-orphan')
    attendances = db.relationship('Attendance', backref='league', lazy='dynamic', cascade='all, delete-orphan')

class Team(db.Model):
    """Team model for team leagues"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    members = db.relationship('BowlerLeague', backref='team', lazy='dynamic')

class Bowler(db.Model):
    """Bowler model"""
    id = db.Column(db.Integer, primary_key=True)
    registration_number = db.Column(db.String(50), unique=True)
    first_name = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    sex = db.Column(db.String(10))
    email = db.Column(db.String(120))
    birthday = db.Column(db.Date)
    address = db.Column(db.String(200))
    suburb = db.Column(db.String(100))
    state = db.Column(db.String(20))
    postcode = db.Column(db.String(10))
    phone = db.Column(db.String(20))
    tba_status = db.Column(db.String(20), default='pending')  # valid, invalid, pending
    tba_last_checked = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    leagues = db.relationship('BowlerLeague', backref='bowler', lazy='dynamic', cascade='all, delete-orphan')
    attendances = db.relationship('Attendance', backref='bowler', lazy='dynamic', cascade='all, delete-orphan')
    locker_rentals = db.relationship('LockerRental', backref='bowler', lazy='dynamic')

class BowlerLeague(db.Model):
    """Association table for bowlers and leagues"""
    id = db.Column(db.Integer, primary_key=True)
    bowler_id = db.Column(db.Integer, db.ForeignKey('bowler.id'))
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'))
    team_id = db.Column(db.Integer, db.ForeignKey('team.id'), nullable=True)
    balance_owing = db.Column(db.Float, default=0)
    joined_date = db.Column(db.DateTime, default=datetime.utcnow)

class Attendance(db.Model):
    """Attendance and payment tracking"""
    id = db.Column(db.Integer, primary_key=True)
    bowler_id = db.Column(db.Integer, db.ForeignKey('bowler.id'))
    league_id = db.Column(db.Integer, db.ForeignKey('league.id'))
    week_number = db.Column(db.Integer)
    date = db.Column(db.Date)
    status = db.Column(db.String(20))  # paid, missed, fixed, na
    payment_method = db.Column(db.String(20))  # cash, card, transfer
    amount_paid = db.Column(db.Float, default=0)
    fine_applied = db.Column(db.Boolean, default=False)
    fine_paid = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    modified_by = db.Column(db.Integer, db.ForeignKey('user.id'))

class Locker(db.Model):
    """Locker model"""
    id = db.Column(db.Integer, primary_key=True)
    number = db.Column(db.String(20), unique=True, nullable=False)
    location = db.Column(db.String(100))
    status = db.Column(db.String(20), default='available')  # available, occupied, maintenance
    rental_rate = db.Column(db.Float)
    rental_period = db.Column(db.String(20))  # monthly, quarterly, annual
    
    # Relationships
    rentals = db.relationship('LockerRental', backref='locker', lazy='dynamic')

class LockerRental(db.Model):
    """Locker rental tracking"""
    id = db.Column(db.Integer, primary_key=True)
    locker_id = db.Column(db.Integer, db.ForeignKey('locker.id'))
    bowler_id = db.Column(db.Integer, db.ForeignKey('bowler.id'))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    payment_status = db.Column(db.String(20))  # paid, overdue, pending
    amount_paid = db.Column(db.Float)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============================================
# AUTHENTICATION
# ============================================

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if current_user.role != 'admin':
            flash('You need administrator privileges to access this page.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

def log_action(action, details=""):
    """Log user actions for audit trail"""
    if current_user.is_authenticated:
        log = AuditLog(
            user_id=current_user.id,
            action=action,
            details=details,
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()
        logging.info(f"User {current_user.username}: {action} - {details}")

def send_email(to_email, subject, body_html, cc_emails=None):
    """Send email using Microsoft 365"""
    msg = MIMEMultipart('alternative')
    msg['From'] = app.config['MAIL_USERNAME']
    msg['To'] = to_email
    msg['Subject'] = subject
    
    if cc_emails:
        msg['Cc'] = ', '.join(cc_emails)
    
    msg.attach(MIMEText(body_html, 'html'))
    
    try:
        server = smtplib.SMTP(app.config['MAIL_SERVER'], app.config['MAIL_PORT'])
        server.starttls()
        server.login(app.config['MAIL_USERNAME'], app.config['MAIL_PASSWORD'])
        
        recipients = [to_email]
        if cc_emails:
            recipients.extend(cc_emails)
            
        server.send_message(msg)
        server.quit()
        
        log_action('EMAIL_SENT', f'To: {to_email}, Subject: {subject}')
        return True
    except Exception as e:
        logging.error(f"Email error: {e}")
        return False

def send_locker_expiry_reminders():
    """Check and send locker rental expiry reminders"""
    today = datetime.now().date()
    
    for days in [30, 14, 7]:
        check_date = today + timedelta(days=days)
        
        expiring_rentals = LockerRental.query.filter(
            LockerRental.end_date == check_date,
            LockerRental.is_active == True
        ).all()
        
        for rental in expiring_rentals:
            bowler = rental.bowler
            locker = rental.locker
            
            # Email to bowler
            if bowler.email:
                body = f"""
                <h2>Locker Rental Expiring Soon</h2>
                <p>Dear {bowler.first_name} {bowler.surname},</p>
                <p>Your rental for <strong>Locker #{locker.number}</strong> at NQ Tenpin Atherton 
                is expiring on <strong>{rental.end_date.strftime('%B %d, %Y')}</strong>.</p>
                <p>Rental Details:</p>
                <ul>
                    <li>Location: {locker.location or 'Main Area'}</li>
                    <li>Rental Rate: ${locker.rental_rate:.2f} per {locker.rental_period}</li>
                </ul>
                <p>Please visit us to renew your locker rental before it expires.</p>
                <p>Thank you,<br>NQ Tenpin Atherton</p>
                """
                send_email(bowler.email, f"Locker Rental Expiring in {days} Days", body)
            
            # Email to staff
            if days in [7, 14]:  # Only alert staff for 14 and 7 day warnings
                staff_body = f"""
                <h2>Locker Expiry Alert</h2>
                <p>Locker #{locker.number} rental is expiring in {days} days.</p>
                <p>Renter: {bowler.first_name} {bowler.surname}</p>
                <p>Phone: {bowler.phone or 'No phone'}</p>
                <p>Email: {bowler.email or 'No email'}</p>
                <p>Expiry Date: {rental.end_date.strftime('%B %d, %Y')}</p>
                """
                for admin_email in app.config['ADMIN_EMAILS']:
                    send_email(admin_email, f"Locker #{locker.number} Expiring in {days} Days", staff_body)

def send_outstanding_balance_reminders():
    """Send weekly reminders for outstanding balances"""
    leagues = League.query.filter_by(is_active=True).all()
    
    for league in leagues:
        bowler_leagues = BowlerLeague.query.filter(
            BowlerLeague.league_id == league.id,
            BowlerLeague.balance_owing > 0
        ).all()
        
        for bl in bowler_leagues:
            bowler = bl.bowler
            if bowler.email and bl.balance_owing > 0:
                body = f"""
                <h2>Outstanding Balance Reminder</h2>
                <p>Dear {bowler.first_name} {bowler.surname},</p>
                <p>You have an outstanding balance for <strong>{league.name}</strong>.</p>
                <p><strong>Amount Owing: ${bl.balance_owing:.2f}</strong></p>
                <p>Please settle your account at your earliest convenience.</p>
                <p>Thank you,<br>NQ Tenpin Atherton</p>
                """
                send_email(bowler.email, f"Outstanding Balance - {league.name}", body)

def send_tba_expiry_notifications():
    """Check and send TBA registration expiry notifications"""
    bowlers = Bowler.query.filter_by(tba_status='invalid').all()
    
    for bowler in bowlers:
        if bowler.email:
            body = f"""
            <h2>TBA Registration Invalid</h2>
            <p>Dear {bowler.first_name} {bowler.surname},</p>
            <p>Our records show your TBA registration (#{bowler.registration_number}) is invalid or expired.</p>
            <p>Please renew your TBA registration to continue participating in sanctioned leagues.</p>
            <p>Thank you,<br>NQ Tenpin Atherton</p>
            """
            send_email(bowler.email, "TBA Registration Invalid", body)

# ============================================
# ROUTES - Authentication
# ============================================

@app.route('/')
def index():
    """Landing page"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username, is_active=True).first()
        
        if user and check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            user.last_login = datetime.utcnow()
            db.session.commit()
            log_action('LOGIN', f'User {username} logged in')
            
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """User logout"""
    log_action('LOGOUT', f'User {current_user.username} logged out')
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard"""
    # Get summary statistics
    total_leagues = League.query.filter_by(is_active=True).count()
    total_bowlers = Bowler.query.count()
    
    # Get TBA registration status summary
    valid_tba = Bowler.query.filter_by(tba_status='valid').count()
    invalid_tba = Bowler.query.filter_by(tba_status='invalid').count()
    pending_tba = Bowler.query.filter_by(tba_status='pending').count()
    
    # Get active leagues
    active_leagues = League.query.filter_by(is_active=True).order_by(League.start_date.desc()).limit(5).all()
    
    # Get recent audit logs
    recent_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(10).all()
    
    return render_template('dashboard.html',
                         total_leagues=total_leagues,
                         total_bowlers=total_bowlers,
                         valid_tba=valid_tba,
                         invalid_tba=invalid_tba,
                         pending_tba=pending_tba,
                         active_leagues=active_leagues,
                         recent_logs=recent_logs)

# ============================================
# ROUTES - League Management
# ============================================

@app.route('/leagues')
@login_required
def leagues():
    """View all leagues"""
    all_leagues = League.query.order_by(League.start_date.desc()).all()
    return render_template('leagues/index.html', leagues=all_leagues)

@app.route('/leagues/create', methods=['GET', 'POST'])
@login_required
def create_league():
    """Create new league wizard"""
    if request.method == 'POST':
        league = League(
            name=request.form.get('name'),
            start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date(),
            finish_date=datetime.strptime(request.form.get('finish_date'), '%Y-%m-%d').date(),
            social_fee=float(request.form.get('social_fee', 0)),
            bowling_fee=float(request.form.get('bowling_fee', 0)),
            has_fines=request.form.get('has_fines') == 'on',
            fine_amount=float(request.form.get('fine_amount', 0)) if request.form.get('has_fines') == 'on' else 0,
            league_type=request.form.get('league_type'),
            players_per_team=int(request.form.get('players_per_team', 0)) if request.form.get('league_type') == 'teams' else None
        )
        
        db.session.add(league)
        db.session.commit()
        
        log_action('CREATE_LEAGUE', f'Created league: {league.name}')
        flash(f'League "{league.name}" created successfully!', 'success')
        
        return redirect(url_for('leagues'))
    
    return render_template('leagues/create.html')

@app.route('/leagues/<int:id>/add-bowlers', methods=['GET', 'POST'])
@login_required
def add_bowlers_to_league(id):
    """Add bowlers to a league"""
    league = League.query.get_or_404(id)
    
    if request.method == 'POST':
        selected_bowler_ids = request.form.getlist('bowler_ids')
        
        for bowler_id in selected_bowler_ids:
            # Check if bowler already in league
            existing = BowlerLeague.query.filter_by(
                bowler_id=bowler_id,
                league_id=id
            ).first()
            
            if not existing:
                bl = BowlerLeague(
                    bowler_id=bowler_id,
                    league_id=id
                )
                db.session.add(bl)
        
        db.session.commit()
        flash(f'Added {len(selected_bowler_ids)} bowlers to {league.name}', 'success')
        return redirect(url_for('attendance', league_id=id))
    
    # Get bowlers not already in this league
    existing_bowler_ids = [bl.bowler_id for bl in league.bowler_leagues]
    available_bowlers = Bowler.query.filter(~Bowler.id.in_(existing_bowler_ids)).all()
    
    return render_template('leagues/add_bowlers.html', 
                         league=league, 
                         available_bowlers=available_bowlers)

@app.route('/leagues/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_league(id):
    """Edit existing league"""
    league = League.query.get_or_404(id)
    
    if request.method == 'POST':
        league.name = request.form.get('name')
        league.start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        league.finish_date = datetime.strptime(request.form.get('finish_date'), '%Y-%m-%d').date()
        league.social_fee = float(request.form.get('social_fee', 0))
        league.bowling_fee = float(request.form.get('bowling_fee', 0))
        league.has_fines = request.form.get('has_fines') == 'on'
        league.fine_amount = float(request.form.get('fine_amount', 0)) if request.form.get('has_fines') == 'on' else 0
        
        db.session.commit()
        log_action('EDIT_LEAGUE', f'Edited league: {league.name}')
        flash('League updated successfully!', 'success')
        
        return redirect(url_for('leagues'))
    
    return render_template('leagues/edit.html', league=league)

@app.route('/leagues/<int:id>/delete', methods=['POST'])
@login_required
def delete_league(id):
    """Delete league"""
    league = League.query.get_or_404(id)
    league_name = league.name
    
    db.session.delete(league)
    db.session.commit()
    
    log_action('DELETE_LEAGUE', f'Deleted league: {league_name}')
    flash(f'League "{league_name}" deleted successfully!', 'success')
    
    return redirect(url_for('leagues'))

@app.route('/leagues/<int:league_id>/teams')
@login_required
def manage_teams(league_id):
    """Manage teams for a league"""
    league = League.query.get_or_404(league_id)
    if league.league_type != 'teams':
        flash('This is not a team league', 'danger')
        return redirect(url_for('leagues'))
    
    teams = Team.query.filter_by(league_id=league_id).all()
    return render_template('leagues/teams.html', league=league, teams=teams)

@app.route('/leagues/<int:league_id>/teams/create', methods=['POST'])
@login_required
def create_team(league_id):
    """Create a new team"""
    league = League.query.get_or_404(league_id)
    team_name = request.form.get('team_name')
    
    team = Team(name=team_name, league_id=league_id)
    db.session.add(team)
    db.session.commit()
    
    flash(f'Team "{team_name}" created', 'success')
    return redirect(url_for('manage_teams', league_id=league_id))

@app.route('/teams/<int:team_id>/members')
@login_required
def manage_team_members(team_id):
    """Assign bowlers to teams"""
    team = Team.query.get_or_404(team_id)
    league = team.league
    
    # Get bowlers in this league not yet in a team
    bowlers_in_league = BowlerLeague.query.filter_by(league_id=league.id, team_id=None).all()
    team_members = BowlerLeague.query.filter_by(team_id=team_id).all()
    
    return render_template('leagues/team_members.html', 
                         team=team, 
                         league=league,
                         available_bowlers=bowlers_in_league,
                         team_members=team_members)

@app.route('/teams/<int:team_id>/add-member/<int:bowler_league_id>', methods=['POST'])
@login_required
def add_to_team(team_id, bowler_league_id):
    """Add bowler to team"""
    bl = BowlerLeague.query.get_or_404(bowler_league_id)
    bl.team_id = team_id
    db.session.commit()
    
    flash('Bowler added to team', 'success')
    return redirect(url_for('manage_team_members', team_id=team_id))

# ============================================
# ROUTES - Bowler Management
# ============================================

@app.route('/bowlers')
@login_required
def bowlers():
    """View all bowlers"""
    all_bowlers = Bowler.query.order_by(Bowler.surname, Bowler.first_name).all()
    return render_template('bowlers/index.html', bowlers=all_bowlers)

@app.route('/bowlers/create', methods=['GET', 'POST'])
@login_required
def create_bowler():
    """Add new bowler"""
    if request.method == 'POST':
        bowler = Bowler(
            registration_number=request.form.get('registration_number'),
            first_name=request.form.get('first_name'),
            surname=request.form.get('surname'),
            sex=request.form.get('sex'),
            email=request.form.get('email'),
            birthday=datetime.strptime(request.form.get('birthday'), '%Y-%m-%d').date() if request.form.get('birthday') else None,
            address=request.form.get('address'),
            suburb=request.form.get('suburb'),
            state=request.form.get('state'),
            postcode=request.form.get('postcode'),
            phone=request.form.get('phone')
        )
        
        db.session.add(bowler)
        db.session.commit()
        
        # Verify TBA registration
        verify_tba_registration(bowler.id)
        
        log_action('CREATE_BOWLER', f'Created bowler: {bowler.first_name} {bowler.surname}')
        flash(f'Bowler "{bowler.first_name} {bowler.surname}" added successfully!', 'success')
        
        return redirect(url_for('bowlers'))
    
    return render_template('bowlers/create.html')

@app.route('/bowlers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_bowler(id):
    """Edit bowler details"""
    bowler = Bowler.query.get_or_404(id)
    
    if request.method == 'POST':
        bowler.first_name = request.form.get('first_name')
        bowler.surname = request.form.get('surname')
        bowler.registration_number = request.form.get('registration_number')
        bowler.sex = request.form.get('sex')
        bowler.email = request.form.get('email')
        bowler.phone = request.form.get('phone')
        bowler.address = request.form.get('address')
        bowler.suburb = request.form.get('suburb')
        bowler.state = request.form.get('state')
        bowler.postcode = request.form.get('postcode')
        
        if request.form.get('birthday'):
            bowler.birthday = datetime.strptime(request.form.get('birthday'), '%Y-%m-%d').date()
        
        db.session.commit()
        
        # Re-verify TBA registration if number changed
        verify_tba_registration(bowler.id)
        
        log_action('EDIT_BOWLER', f'Edited bowler: {bowler.first_name} {bowler.surname}')
        flash('Bowler updated successfully!', 'success')
        
        return redirect(url_for('bowlers'))
    
    return render_template('bowlers/edit.html', bowler=bowler)

@app.route('/bowlers/<int:id>/delete', methods=['POST'])
@login_required
def delete_bowler(id):
    """Delete bowler"""
    bowler = Bowler.query.get_or_404(id)
    name = f"{bowler.first_name} {bowler.surname}"
    
    db.session.delete(bowler)
    db.session.commit()
    
    log_action('DELETE_BOWLER', f'Deleted bowler: {name}')
    flash(f'Bowler "{name}" deleted successfully!', 'success')
    
    return redirect(url_for('bowlers'))

@app.route('/bowlers/import', methods=['GET', 'POST'])
@login_required
def import_bowlers():
    """Import bowlers from CSV"""
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        file = request.files['file']
        
        if file.filename == '':
            flash('No file selected', 'danger')
            return redirect(request.url)
        
        if file and file.filename.endswith('.csv'):
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_reader = csv.DictReader(stream)
            
            count = 0
            errors = []
            skipped = 0
            
            for row_num, row in enumerate(csv_reader, 1):
                try:
                    # Get registration number and strip whitespace
                    reg_num = (row.get('Registration#') or '').strip()
                    
                    # Skip empty rows
                    if not reg_num:
                        skipped += 1
                        continue
                    
                    # Check if bowler already exists
                    existing = Bowler.query.filter_by(registration_number=reg_num).first()
                    
                    if existing:
                        skipped += 1
                        continue
                    
                    # Parse birthday safely
                    birthday = None
                    birthday_str = (row.get('Birthday') or '').strip()
                    if birthday_str:
                        try:
                            birthday = datetime.strptime(birthday_str, '%d/%m/%Y').date()
                        except:
                            birthday = None
                    
                    # Create bowler
                    bowler = Bowler(
                        registration_number=reg_num,
                        first_name=(row.get('First Name') or '').strip() or 'Unknown',
                        surname=(row.get('Surname') or '').strip() or 'Unknown',
                        sex=(row.get('SEX') or '').strip()[:1].upper() if row.get('SEX') else None,
                        email=(row.get('Email') or '').strip() or None,
                        birthday=birthday,
                        address=(row.get('Address') or '').strip() or None,
                        suburb=(row.get('Suburb') or '').strip() or None,
                        state=(row.get('State') or '').strip() or None,
                        postcode=(row.get('P/C') or '').strip() or None,
                        phone=(row.get('Phone') or '').strip() or None
                    )
                    
                    db.session.add(bowler)
                    count += 1
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    continue
            
            try:
                db.session.commit()
                
                # Verify TBA registrations for new bowlers
                new_bowlers = Bowler.query.filter_by(tba_status='pending').all()
                for bowler in new_bowlers:
                    verify_tba_registration(bowler.id)
                
                log_action('IMPORT_BOWLERS', f'Imported {count} bowlers')
                
                if errors:
                    flash(f'Imported {count} bowlers. Skipped {skipped} duplicates. {len(errors)} errors.', 'warning')
                else:
                    flash(f'Successfully imported {count} bowlers! Skipped {skipped} duplicates.', 'success')
                    
            except Exception as e:
                db.session.rollback()
                flash(f'Database error: {str(e)}', 'danger')
                return redirect(request.url)
            
            return redirect(url_for('bowlers'))
        else:
            flash('File must be a CSV', 'danger')
            return redirect(request.url)
    
    return render_template('bowlers/import.html')

def verify_tba_registration(bowler_id):
    """Dummy function - TBA verification disabled"""
    bowler = Bowler.query.get(bowler_id)
    if bowler:
        bowler.tba_status = 'valid'  # Always mark as valid
        bowler.tba_last_checked = datetime.utcnow()
        db.session.commit()

@app.route('/bowlers/verify-tba', methods=['POST'])
@login_required
def verify_all_tba():
    """Verify all TBA registrations"""
    bowlers = Bowler.query.all()
    count = 0
    
    for bowler in bowlers:
        verify_tba_registration(bowler.id)
        count += 1
    
    log_action('VERIFY_TBA', f'Verified {count} TBA registrations')
    flash(f'Verified {count} TBA registrations', 'success')
    
    return redirect(url_for('bowlers'))

# ============================================
# ROUTES - Attendance & Payment
# ============================================

@app.route('/attendance/<int:league_id>')
@login_required
def attendance(league_id):
    """Attendance and payment grid"""
    league = League.query.get_or_404(league_id)
    
    # Get all bowlers in this league
    if league.league_type == 'teams':
        # Get bowlers WITH teams first, sorted by team name
        with_teams = BowlerLeague.query.filter_by(league_id=league_id).filter(
            BowlerLeague.team_id != None
        ).join(Team).order_by(Team.name).all()
        
        # Get bowlers WITHOUT teams
        without_teams = BowlerLeague.query.filter_by(league_id=league_id, team_id=None).all()
        
        bowler_leagues = with_teams + without_teams
    else:
        bowler_leagues = BowlerLeague.query.filter_by(league_id=league_id).all()
    
    # Calculate weeks in league
    weeks = []
    current_date = league.start_date
    week_num = 1
    
    while current_date <= league.finish_date:
        weeks.append({'number': week_num, 'date': current_date})
        current_date += timedelta(days=7)
        week_num += 1
    
    # Get attendance records
    attendance_records = {}
    for bl in bowler_leagues:
        bowler_attendance = Attendance.query.filter_by(
            bowler_id=bl.bowler_id, 
            league_id=league_id
        ).all()
        attendance_records[bl.bowler_id] = {a.week_number: a for a in bowler_attendance}

        # Update all balances before displaying
    for bl in bowler_leagues:
        update_bowler_balance(bl.bowler_id, league_id)
    
    return render_template('attendance/grid.html', 
                         league=league,
                         bowler_leagues=bowler_leagues,
                         weeks=weeks,
                         attendance_records=attendance_records)

@app.route('/attendance/update', methods=['POST'])
@login_required
def update_attendance():
    """Update attendance status via AJAX"""
    data = request.json
    
    bowler_id = data.get('bowler_id')
    league_id = data.get('league_id')
    week_number = data.get('week_number')
    status = data.get('status')
    amount = data.get('amount', 0)
    
    # Find or create attendance record
    attendance = Attendance.query.filter_by(
        bowler_id=bowler_id,
        league_id=league_id,
        week_number=week_number
    ).first()
    
    if not attendance:
        attendance = Attendance(
            bowler_id=bowler_id,
            league_id=league_id,
            week_number=week_number,
            status=status,
            amount_paid=amount,
            fine_paid=False,
            fine_applied=False
        )
        db.session.add(attendance)
    else:
        attendance.status = status
        attendance.amount_paid = amount
        if status == 'fixed':
            attendance.fine_paid = True
        elif status == 'missed':
            attendance.fine_paid = False
    
    attendance.modified_by = current_user.id
    db.session.commit()
    
    # Update balance and return it
    new_balance = update_bowler_balance(bowler_id, league_id)
    
    return jsonify({'success': True, 'balance': new_balance})

def update_bowler_balance(bowler_id, league_id):
    """Calculate and update bowler's balance"""
    bowler_league = BowlerLeague.query.filter_by(
        bowler_id=bowler_id,
        league_id=league_id
    ).first()
    
    if not bowler_league:
        return 0
    
    league = League.query.get(league_id)
    
    # Get all attendance records
    attendances = Attendance.query.filter_by(
        bowler_id=bowler_id,
        league_id=league_id
    ).all()
    
    total_owed = 0
    
    for attendance in attendances:
        if attendance.status == 'missed':
            # Missed week = social fee + fine (always both for missed)
            total_owed += league.social_fee
            if league.has_fines:
                total_owed += league.fine_amount
        elif attendance.status == 'fixed':
            # Fixed = missed week but fine is paid, so just social
            total_owed += league.social_fee
        elif attendance.status == 'paid':
            # Paid = they attended and paid, so no debt for this week
            pass
    
    # Subtract actual payments
    total_paid = db.session.query(db.func.sum(Attendance.amount_paid)).filter_by(
        bowler_id=bowler_id,
        league_id=league_id
    ).scalar() or 0
    
    bowler_league.balance_owing = total_owed - total_paid
    db.session.commit()
    
    return bowler_league.balance_owing

# ============================================
# ROUTES - Locker Management
# ============================================

@app.route('/lockers')
@login_required
def lockers():
    """View all lockers"""
    all_lockers = Locker.query.order_by(Locker.number).all()
    return render_template('lockers/index.html', lockers=all_lockers)

@app.route('/lockers/create', methods=['GET', 'POST'])
@login_required
def create_locker():
    """Add new locker"""
    if request.method == 'POST':
        locker = Locker(
            number=request.form.get('number'),
            location=request.form.get('location'),
            rental_rate=float(request.form.get('rental_rate', 0)),
            rental_period=request.form.get('rental_period')
        )
        
        db.session.add(locker)
        db.session.commit()
        
        log_action('CREATE_LOCKER', f'Created locker: {locker.number}')
        flash(f'Locker {locker.number} created successfully!', 'success')
        
        return redirect(url_for('lockers'))
    
    return render_template('lockers/create.html')

@app.route('/lockers/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_locker(id):
    """Edit locker details"""
    locker = Locker.query.get_or_404(id)
    
    if request.method == 'POST':
        locker.number = request.form.get('number')
        locker.location = request.form.get('location')
        locker.rental_rate = float(request.form.get('rental_rate', 0))
        locker.rental_period = request.form.get('rental_period')
        
        db.session.commit()
        log_action('EDIT_LOCKER', f'Edited locker: {locker.number}')
        flash('Locker updated successfully!', 'success')
        
        return redirect(url_for('lockers'))
    
    return render_template('lockers/edit.html', locker=locker)

@app.route('/lockers/<int:id>/delete', methods=['POST'])
@login_required
def delete_locker(id):
    """Delete locker"""
    locker = Locker.query.get_or_404(id)
    locker_number = locker.number
    
    db.session.delete(locker)
    db.session.commit()
    
    log_action('DELETE_LOCKER', f'Deleted locker: {locker_number}')
    flash(f'Locker {locker_number} deleted successfully!', 'success')
    
    return redirect(url_for('lockers'))

@app.route('/lockers/<int:id>/rent', methods=['GET', 'POST'])
@login_required
def rent_locker(id):
    """Rent locker to bowler"""
    locker = Locker.query.get_or_404(id)
    
    if request.method == 'POST':
        rental = LockerRental(
            locker_id=locker.id,
            bowler_id=int(request.form.get('bowler_id')),
            start_date=datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date(),
            end_date=datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date(),
            payment_status='paid' if request.form.get('paid_now') == 'on' else 'pending',
            amount_paid=float(request.form.get('amount_paid', 0))
        )
        
        locker.status = 'occupied'
        
        db.session.add(rental)
        db.session.commit()
        
        log_action('RENT_LOCKER', f'Rented locker {locker.number}')
        flash(f'Locker {locker.number} rented successfully!', 'success')
        
        return redirect(url_for('lockers'))
    
    bowlers = Bowler.query.order_by(Bowler.surname, Bowler.first_name).all()
    return render_template('lockers/rent.html', locker=locker, bowlers=bowlers)

# ============================================
# ROUTES - User Management
# ============================================

@app.route('/users')
@admin_required
def users():
    """View all users (admin only)"""
    all_users = User.query.all()
    audit_logs = AuditLog.query.order_by(AuditLog.timestamp.desc()).limit(20).all()
    return render_template('users/index.html', users=all_users, audit_logs=audit_logs)

@app.route('/users/create', methods=['GET', 'POST'])
@admin_required
def create_user():
    """Create new user (admin only)"""
    if request.method == 'POST':
        user = User(
            username=request.form.get('username'),
            email=request.form.get('email'),
            password_hash=generate_password_hash(request.form.get('password')),
            role=request.form.get('role', 'staff')
        )
        
        db.session.add(user)
        db.session.commit()
        
        log_action('CREATE_USER', f'Created user: {user.username}')
        flash(f'User "{user.username}" created successfully!', 'success')
        
        return redirect(url_for('users'))
    
    return render_template('users/create.html')

@app.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(id):
    """Edit user details (admin only)"""
    user = User.query.get_or_404(id)
    
    if request.method == 'POST':
        user.email = request.form.get('email')
        
        # Only update role if not editing self
        if user.id != current_user.id:
            user.role = request.form.get('role', 'staff')
            user.is_active = request.form.get('is_active') == 'on'
        
        # Update password if provided
        new_password = request.form.get('new_password')
        if new_password:
            user.password_hash = generate_password_hash(new_password)
        
        db.session.commit()
        log_action('EDIT_USER', f'Edited user: {user.username}')
        flash('User updated successfully!', 'success')
        
        return redirect(url_for('users'))
    
    return render_template('users/edit.html', user=user)

@app.route('/users/<int:id>/activate', methods=['POST'])
@admin_required
def activate_user(id):
    """Activate user account"""
    user = User.query.get_or_404(id)
    user.is_active = True
    db.session.commit()
    
    log_action('ACTIVATE_USER', f'Activated user: {user.username}')
    flash(f'User "{user.username}" activated!', 'success')
    
    return redirect(url_for('users'))

@app.route('/teams/<int:team_id>/delete', methods=['POST'])
@login_required
def delete_team(team_id):
    """Delete a team"""
    team = Team.query.get_or_404(team_id)
    league_id = team.league_id
    
    # Remove all bowlers from this team first
    BowlerLeague.query.filter_by(team_id=team_id).update({'team_id': None})
    
    db.session.delete(team)
    db.session.commit()
    
    flash(f'Team "{team.name}" deleted', 'success')
    return redirect(url_for('manage_teams', league_id=league_id))

@app.route('/teams/remove-member/<int:bowler_league_id>', methods=['POST'])
@login_required
def remove_from_team(bowler_league_id):
    """Remove bowler from team"""
    bl = BowlerLeague.query.get_or_404(bowler_league_id)
    team_id = bl.team_id
    bl.team_id = None
    db.session.commit()
    
    flash('Bowler removed from team', 'success')
    return redirect(url_for('manage_team_members', team_id=team_id))

@app.route('/users/<int:id>/deactivate', methods=['POST'])
@admin_required
def deactivate_user(id):
    """Deactivate user account"""
    user = User.query.get_or_404(id)
    
    if user.id == current_user.id:
        flash('You cannot deactivate your own account!', 'danger')
    else:
        user.is_active = False
        db.session.commit()
        
        log_action('DEACTIVATE_USER', f'Deactivated user: {user.username}')
        flash(f'User "{user.username}" deactivated!', 'success')
    
    return redirect(url_for('users'))

# ============================================
# ROUTES - Reports
# ============================================

@app.route('/reports')
@login_required
def reports():
    """Reports dashboard"""
    return render_template('reports/index.html')

@app.route('/reports/financial/<int:league_id>')
@login_required
def financial_report(league_id):
    """Generate financial report"""
    league = League.query.get_or_404(league_id)
    
    # Calculate totals
    total_expected = db.session.query(db.func.sum(
        BowlerLeague.balance_owing
    )).filter_by(league_id=league_id).scalar() or 0
    
    total_received = db.session.query(db.func.sum(
        Attendance.amount_paid
    )).filter_by(league_id=league_id).scalar() or 0
    
    total_outstanding = total_expected - total_received
    
    return render_template('reports/financial.html',
                         league=league,
                         total_expected=total_expected,
                         total_received=total_received,
                         total_outstanding=total_outstanding)

# ============================================
# ROUTES - Email Management
# ============================================

@app.route('/admin/test-email')
@admin_required
def test_email():
    """Test email configuration"""
    test_sent = send_email(
        current_user.email,
        "Test Email - NQ Tenpin",
        "<h2>Test Email</h2><p>Email configuration is working correctly.</p>"
    )
    if test_sent:
        flash('Test email sent successfully!', 'success')
    else:
        flash('Failed to send test email. Check configuration.', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/admin/send-reminders')
@admin_required
def manual_send_reminders():
    """Manually trigger reminder emails"""
    send_locker_expiry_reminders()
    send_outstanding_balance_reminders()
    flash('Reminder emails sent', 'success')
    return redirect(url_for('dashboard'))

@app.route('/leagues/<int:league_id>/email-bowlers', methods=['GET', 'POST'])
@login_required
def email_league_bowlers(league_id):
    """Send bulk email to all bowlers in a league"""
    league = League.query.get_or_404(league_id)
    
    if request.method == 'POST':
        subject = request.form.get('subject')
        message = request.form.get('message')
        
        bowler_leagues = BowlerLeague.query.filter_by(league_id=league_id).all()
        sent_count = 0
        
        for bl in bowler_leagues:
            if bl.bowler.email:
                body = f"""
                <h2>{subject}</h2>
                <p>Dear {bl.bowler.first_name} {bl.bowler.surname},</p>
                {message}
                <p>Thank you,<br>NQ Tenpin Atherton</p>
                """
                if send_email(bl.bowler.email, subject, body):
                    sent_count += 1
        
        flash(f'Email sent to {sent_count} bowlers', 'success')
        return redirect(url_for('leagues'))
    
    return render_template('emails/compose.html', league=league)

# ============================================
# INITIALIZATION
# ============================================

def init_db():
    """Initialize database with default admin user"""
    with app.app_context():
        db.create_all()
        
        # Create default admin if doesn't exist
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin = User(
                username='admin',
                email='admin@nqtenpin.com',
                password_hash=generate_password_hash('admin123'),
                role='admin'
            )
            db.session.add(admin)
            db.session.commit()
            print("Default admin user created (username: admin, password: admin123)")

# Initialize scheduler for automated emails
scheduler = BackgroundScheduler()

def scheduled_email_tasks():
    """Run all scheduled email tasks"""
    with app.app_context():
        send_locker_expiry_reminders()
        
        # Send balance reminders on Mondays
        if datetime.now().weekday() == 0:
            send_outstanding_balance_reminders()
        
        # Send TBA notifications on Fridays
        if datetime.now().weekday() == 4:
            send_tba_expiry_notifications()

# Schedule daily check at 9 AM
scheduler.add_job(func=scheduled_email_tasks, trigger="cron", hour=9, minute=0)
scheduler.start()

# Shut down scheduler when app stops
atexit.register(lambda: scheduler.shutdown())

if __name__ == '__main__':
    init_db()
    app.run(host='0.0.0.0', port=2019, debug=True)
