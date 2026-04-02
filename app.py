from flask import Flask, render_template, redirect, url_for, flash, request, session, abort
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, Length, ValidationError
from datetime import datetime
import os
from sqlalchemy.exc import IntegrityError

# Initialize Flask app
app = Flask(__name__, template_folder='client/templates')

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.abspath(os.path.join(app.instance_path, "voters.db"))}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['ADMIN_KEY'] = os.environ.get('ADMIN_KEY', 'admin123')

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Database Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)

class Voter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    voter_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    fathers_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    assembly_constituency = db.Column(db.String(100), nullable=False)
    parliamentary_constituency = db.Column(db.String(100), nullable=False)
    booth_location = db.Column(db.String(150), nullable=False)
    polling_date = db.Column(db.Date, nullable=False)

# Form Classes
class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Login')

class AdminLoginForm(FlaskForm):
    email = StringField('Admin Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Admin Login')

class RegistrationForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Sign Up')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered')

class AdminVerifyForm(FlaskForm):
    key = PasswordField('Admin Key', validators=[DataRequired()])
    submit = SubmitField('Verify')

class VoterVerifyForm(FlaskForm):
    voter_id = StringField('Voter ID', validators=[DataRequired()])
    submit = SubmitField('Verify')

class BulkAddForm(FlaskForm):
    voter_data = TextAreaField('Voter Data', validators=[DataRequired()])
    submit = SubmitField('Add Voters')

class DeleteAllForm(FlaskForm):
    submit = SubmitField('Delete All Voters')

# Login Manager Loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Database Initialization
_initialized = False

def initialize():
    global _initialized
    if not _initialized:
        os.makedirs(app.instance_path, exist_ok=True)
        with app.app_context():
            db.create_all()
            if not User.query.filter_by(email='admin@example.com').first():
                hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
                admin = User(email='admin@example.com', password=hashed_password, is_admin=True)
                db.session.add(admin)
                db.session.commit()
            _initialized = True

@app.cli.command('init-db')
def init_db_command():
    """Initialize the database."""
    initialize()
    print('Initialized the database.')

# Application Routes
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('dashboard'))
        flash('Invalid email or password', 'danger')
    return render_template('login.html', form=form)

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated and current_user.is_admin:
        return redirect(url_for('admin_verify'))
    form = AdminLoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.is_admin and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user)
            return redirect(url_for('admin_verify'))
        flash('Admin login failed', 'danger')
    return render_template('admin_login.html', form=form)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(email=form.email.data, password=hashed_password)
        try:
            db.session.add(user)
            db.session.commit()
            flash('Account created! Please login', 'success')
            return redirect(url_for('login'))
        except IntegrityError:
            db.session.rollback()
            flash('Email already registered', 'danger')
    return render_template('signup.html', form=form)

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        abort(403)
    
    voters_count = Voter.query.count()
    try:
        db_size = os.path.getsize('instance/voters.db') / (1024 * 1024)
    except Exception:
        db_size = 0
    
    return render_template('admin_dashboard.html',
                         voters_count=voters_count,
                         db_size=round(db_size, 2))

@app.route('/voter_verify', methods=['GET', 'POST'])
@login_required
def voter_verify():
    form = VoterVerifyForm()
    result = None
    if form.validate_on_submit():
        voter = Voter.query.filter_by(voter_id=form.voter_id.data).first()
        if voter:
            result = {
                'name': voter.name,
                'age': voter.age,
                'gender': voter.gender,
                'fathers_name': voter.fathers_name,
                'address': voter.address,
                'assembly_constituency': voter.assembly_constituency,
                'parliamentary_constituency': voter.parliamentary_constituency,
                'booth_location': voter.booth_location,
                'polling_date': voter.polling_date.strftime('%Y-%m-%d')
            }
            flash('Voter verification successful!', 'success')
        else:
            flash('Voter ID not found', 'danger')
    return render_template('voter_verify.html', form=form, result=result)

@app.route('/admin/verify', methods=['GET', 'POST'])
@login_required
def admin_verify():
    if not current_user.is_admin:
        abort(403)
    form = AdminVerifyForm()
    if form.validate_on_submit():
        if form.key.data == app.config['ADMIN_KEY']:
            session['admin_verified'] = True
            return redirect(url_for('voter_management'))
        flash('Invalid admin key', 'danger')
    return render_template('admin_verify.html', form=form)

@app.route('/admin/voter_management')
@login_required
def voter_management():
    if not current_user.is_admin or not session.get('admin_verified'):
        abort(403)
    return render_template('voter_management.html')

@app.route('/bulk_add_voters', methods=['POST'])
@login_required
def bulk_add_voters():
    if not current_user.is_admin or not session.get('admin_verified'):
        abort(403)
    
    voter_data = request.form.get('voter_data')
    
    try:
        lines = voter_data.split('\n')
        added_count = 0
        errors = []
        
        for i, line in enumerate(lines, 1):
            try:
                if not line.strip():
                    continue
                    
                parts = [part.strip() for part in line.split(',')]
                if len(parts) != 10:
                    raise ValueError(f"Invalid number of fields (expected 10, got {len(parts)})")
                
                voter = Voter(
                    voter_id=parts[0],
                    booth_location=parts[1],
                    name=parts[2],
                    age=int(parts[3]),
                    gender=parts[4],
                    fathers_name=parts[5],
                    address=parts[6],
                    assembly_constituency=parts[7],
                    parliamentary_constituency=parts[8],
                    polling_date=datetime.strptime(parts[9], '%Y-%m-%d')
                )
                
                db.session.add(voter)
                added_count += 1
                
            except Exception as e:
                errors.append(f"Line {i}: {str(e)}")
        
        db.session.commit()
        if errors:
            flash(f'Added {added_count} voters with {len(errors)} errors', 'warning')
            flash('Errors: ' + '; '.join(errors), 'warning')
        else:
            flash(f'Successfully added {added_count} voters', 'success')
            
    except Exception as e:
        db.session.rollback()
        flash(f'Bulk upload failed: {str(e)}', 'danger')
    
    return redirect(url_for('voter_management'))

@app.route('/show_all_data', methods=['GET'])
@login_required
def show_all_data():
    if not current_user.is_admin or not session.get('admin_verified'):
        abort(403)
    
    search_query = request.args.get('search', '').strip()
    if search_query:
        voters = Voter.query.filter(Voter.voter_id.contains(search_query)).all()
    else:
        voters = Voter.query.all()
    return render_template('voter_management.html', voters=voters)

@app.route('/delete_voter/<string:voter_id>', methods=['POST'])
@login_required
def delete_voter(voter_id):
    if not current_user.is_admin or not session.get('admin_verified'):
        abort(403)
    
    voter = Voter.query.filter_by(voter_id=voter_id).first()
    if voter:
        db.session.delete(voter)
        db.session.commit()
        flash('Voter deleted successfully', 'success')
    else:
        flash('Voter not found', 'danger')
    return redirect(url_for('show_all_data'))

@app.route('/delete_all_data', methods=['POST'])
@login_required
def delete_all_data():
    if not current_user.is_admin or not session.get('admin_verified'):
        abort(403)
    
    try:
        num_rows_deleted = db.session.query(Voter).delete()
        db.session.commit()
        flash(f'Successfully deleted {num_rows_deleted} voters.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting voters: {str(e)}', 'danger')
    
    return redirect(url_for('voter_management'))

@app.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)