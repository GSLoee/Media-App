import os
from flask import Flask, render_template, request, flash, redirect, session, g
from sqlalchemy.exc import IntegrityError
from models import connect_db, db, bcrypt, User, Saved, Finished
from forms import RegistrationForm, LoginForm
from api import BASE_URL, TRENDING, POSTER_PATH, API_KEY, ACCESS_TOKEN
import requests

CURR_USER_KEY = "curr_user"

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'postgresql:///media_db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = True
app.config['SECRET_KEY'] = 'secretthings'

connect_db(app)
with app.app_context():
    db.create_all()

@app.before_request
def add_user_to_g():
    """If a user is logged in, add the user to Flask global"""
    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])
    else:
        g.user = None

def do_login(user):
    session[CURR_USER_KEY] = user.id

def do_logout():
    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]

@app.route('/')
def home():
    # user = User.query.get_or_404()
    url = TRENDING
    trending = requests.get(url).json()
    return render_template('base.html', trending=trending)
    
@app.route('/signup', methods=["GET", "POST"])
def signup():
    form = RegistrationForm()

    if form.validate_on_submit():
        try:
            user = User.signup(
                username=form.username.data,
                password=form.password.data,
                image_url=form.image_url.data or User.image_url.default.arg,
            )
            db.session.commit()
        
        except IntegrityError:
            flash('Username is taken, please choose a new username', 'danger')
            return render_template('signup.html', form=form)
        
        do_login(user)
        return redirect('/')
    
    else: 
        return render_template('signup.html', form=form)

@app.route('/login', methods=["GET", "POST"])
def login():
    form = LoginForm()

    if form.validate_on_submit():
        user = User.authenticate(form.username.data, form.password.data)

        if user: 
            do_login(user)
            # flash(f'Hello, {user.username}!', "success")
            return redirect('/')
        
        flash('Invalid credentials.', 'danger')
    
    return render_template('login.html', form=form)

@app.route('/logout')
def logout():
    do_logout()
    flash(f'You have been logged out')
    return redirect('/login')
   


@app.route('/movie/<int:movie_id>')
def movie_info(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?{API_KEY}&language=en-US"
    movie_data = requests.get(url).json()
    
    return render_template('movie_info.html', movie_data=movie_data)

@app.route('/tv/<int:series_id>')
def series_info(series_id):
    url = f'https://api.themoviedb.org/3/tv/{series_id}?{API_KEY}&language=en-US'
    tv_data = requests.get(url).json()

    return render_template('tv_info.html', tv_data=tv_data)

@app.route('/search/multi/', methods=['POST', 'GET'])
def search():
    media_name = request.args.get('query')
    url = f'https://api.themoviedb.org/3/search/multi?{API_KEY}&query={media_name}&include_adult=true&language=en-US'
    search_data = requests.get(url).json()
    return render_template('search.html', search_data=search_data)

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/watchlist-movie/<int:user_id>')
def watchlist_movie(user_id):
    user = User.query.get_or_404(user_id)
    if not CURR_USER_KEY in session:
        flash('Unauthorized access', 'danger')
    completed_list = Finished.query.filter_by(user_id=user_id).all()
    completed = []
    for item in completed_list:
        url = f"https://api.themoviedb.org/3/movie/{item.media_id}?{API_KEY}&language=en-US"
        completed.append(requests.get(url).json())
    print(completed)

    return render_template('completed.html', user=user, completed_list=completed_list, completed=completed)

@app.route('/watchlist-tv/<int:user_id>')
def watchlist_tv(user_id):
    user = User.query.get_or_404(user_id)
    if CURR_USER_KEY not in session:
        flash('Unauthorized access', 'danger')
        return redirect('/login')  # Redirect to login page or handle unauthorized access

    watchlist = Saved.query.filter_by(user_id=user_id).all()
    tv_data = []
    movie_data = []
    # Iterate through each item in the watchlist
    for item in watchlist:
        # Build the URL for each media_id
        tv_url = f'https://api.themoviedb.org/3/tv/{item.media_id}?{API_KEY}&language=en-US'
        movie_url = f'https://api.themoviedb.org/3/movie/{item.media_id}?{API_KEY}&language=en-US'
        
        # Make the API request for each media_id and append the response to tv_data
        tv_data.append(requests.get(tv_url).json())
        movie_data.append(requests.get(movie_url).json())

    return render_template('watchlist.html', user=user, tv_data=tv_data, watchlist=watchlist, movie_data=movie_data)
    

@app.route('/watchlist/add/<int:media_id>', methods=['POST'])
def add_to_watchlist(media_id):
    # url = f"https://api.themoviedb.org/3/movie/{movie_id}?{API_KEY}&language=en-US" 
    if not g.user:
        flash('Must be logged in')
    watchlist_item = Saved.query.filter_by(user_id=g.user.id, media_id=media_id).first()
    if watchlist_item:
        return redirect(f'/watchlist-tv/{g.user.id}')          
    watchlist = Saved(user_id=g.user.id, media_id=media_id)
    db.session.add(watchlist)
    db.session.commit()
    return redirect(f'/watchlist-tv/{g.user.id}')

@app.route('/completed/add/<int:movie_id>', methods=['POST'])
def add_to_complete(movie_id):
    if not g.user:
        flash('Must be logged in')
    watchlist_item = Finished.query.filter_by(user_id=g.user.id, media_id=movie_id).first()
    if watchlist_item:
        return redirect(f'/watchlist-movie/{g.user.id}')
    finished = Finished(user_id=g.user.id, media_id=movie_id)
    db.session.add(finished)
    db.session.commit()
    return redirect(f'/watchlist-movie/{g.user.id}')

@app.route('/delete/<int:media_id>', methods=['POST'])
def delete_movie(media_id):
    if not g.user:
        flash('Unauthorized access', 'danger')
        return redirect('/login')
    
    # Check if the item is a TV show or a movie
    watchlist_item = Finished.query.filter_by(user_id=g.user.id, media_id=media_id).first()
    finished_item = Saved.query.filter_by(user_id=g.user.id, media_id=media_id).first()
    if watchlist_item:
        db.session.delete(watchlist_item)
        db.session.commit()
        return redirect(f'/watchlist-movie/{g.user.id}')
    else:
        db.session.delete(finished_item)
        db.session.commit()
        return redirect(f'/watchlist-tv/{g.user.id}')