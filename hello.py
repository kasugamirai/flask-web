from flask import Flask
from markupsafe import escape
from flask import render_template
from flask import request, flash
from flask import url_for, redirect
from flask_sqlalchemy import SQLAlchemy
import os
import click
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from flask_login import UserMixin

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:////' + os.path.join(app.root_path, 'data.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'dev'
db = SQLAlchemy(app)
from werkzeug.security import generate_password_hash, check_password_hash

login_manager = LoginManager(app)  
login_manager.login_view = 'login'
@login_manager.user_loader
def load_user(user_id):  
    user = User.query.get(int(user_id))  
    return user 



class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20))
    username = db.Column(db.String(20))
    password_hash = db.Column(db.String(128))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)


class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(60))
    year = db.Column(db.String(4))

class Music(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(20))
    artist = db.Column(db.String(20))
    album = db.Column(db.String(20))
    grouping = db.Column(db.String(20))



@app.context_processor
def inject_music():
    musics = Music.query.all()
    return dict(musics = musics)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if not current_user.is_authenticated:
            return redirect(url_for('index'))
        title = request.form.get('title') 
        album = request.form.get('album')
        artist = request.form.get('artist')
        grouping = request.form.get('grouping')
        if not title or not album:
            flash('Invalid input.') 
            return redirect(url_for('index'))
        music = Music(title=title, album=album, artist=artist, grouping=grouping)
        db.session.add(music)
        db.session.commit()
        flash('Item created.')
        return redirect(url_for('index'))
        
    return render_template('index.html')

@app.route('/music/edit/<int:music_id>', methods=['GET', 'POST'])
@login_required
def edit(music_id):
    music = Music.query.get_or_404(music_id)

    if request.method == 'POST': 
        title = request.form.get('title') 
        album = request.form.get('album')
        artist = request.form.get('artist')
        grouping = request.form.get('grouping')

        if not title or not album:
            flash('Invalid input.')
            return redirect(url_for('edit', music_id=music_id))
        music.title=title
        music.album=album
        music.artist=artist
        music.grouping=grouping
        db.session.commit()
        flash('Item updated.')
        return redirect(url_for('index'))

    return render_template('edit.html', music=music)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if not username or not password:
            flash('Invalid input.')
            return redirect(url_for('login'))


        if User.query.filter_by(username=username).first():
            user = User.query.filter_by(username=username).first()
            if user.validate_password(password):
                login_user(User.query.filter_by(username=username).first())  
                flash('Login success.')
                return redirect(url_for('index')) 

        flash('Invalid username or password.') 
        return redirect(url_for('login')) 
        
    return render_template('login.html')

@app.route('/logout')
@login_required 
def logout():
    logout_user()
    flash('Goodbye.')
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User(username=username, name='Admin')
        user.set_password(password) 
        db.session.add(user)
        db.session.commit()
        flash('Item created.')
        return redirect(url_for('index'))
    return render_template('register.html')

@app.route('/music/delete/<int:music_id>', methods=['POST'])
@login_required
def delete(music_id):
    music = Music.query.get_or_404(music_id)
    db.session.delete(music)
    db.session.commit()
    flash('Item deleted.')
    return redirect(url_for('index'))

@app.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        name = request.form['name']

        if not name or len(name) > 20:
            flash('Invalid input.')
            return redirect(url_for('settings'))

        current_user.username = name
        db.session.commit()
        flash('Settings updated.')
        return redirect(url_for('index'))

    return render_template('settings.html')

@app.cli.command()
@click.option('--username', prompt=True, help='The username used to login.')
@click.option('--password', prompt=True, hide_input=True, confirmation_prompt=True, help='The password used to login.')
def admin(username, password):
    """Create user."""
    db.create_all()

    user = User.query.first()
    if user is not None:
        click.echo('Updating user...')
        user.username = username
        user.set_password(password)
    else:
        click.echo('Creating user...')
        user = User(username=username, name='Admin')
        user.set_password(password)
        db.session.add(user)

    db.session.commit()
    click.echo('Done.')

@app.cli.command()
def creatmusic():
    musics = [
        {'title': 'Vroom Vroom', 'artist': 'R3BIRTH', 'album': 'Vroom Vroom - EP', 'grouping': 'Love live'},
        {'title': 'Tracing Defender', 'artist': 'ストレイライト', 'album': 'PANOR@MA WING 06', 'grouping': 'Idolmaster'}
    ]
    for m in musics:
        music = Music(title = m['title'], artist = m['artist'], album = m['album'], grouping = m['grouping'])
        db.session.add(music)
    db.session.commit()
    click.echo('Done')


@app.cli.command() 
@click.option('--drop', is_flag=True, help='Create after drop.')
def initdb(drop):
    """Initialize the database."""
    if drop:
        db.drop_all()
    db.create_all()
    click.echo('Initialized database.')



