import os
from flask import Flask, render_template, request, flash, redirect, session, g
from sqlalchemy.exc import IntegrityError
from models import connect_db, db, bcrypt, User, Saved, Finished
from forms import RegistrationForm, LoginForm
import requests
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

CURR_USER_KEY = "curr_user"

# Get API keys from environment variables
API_KEY = os.getenv('API_KEY')
ACCESS_TOKEN = os.getenv('ACCESS_TOKEN')

# Define constants using the API keys
BASE_URL = f"https://api.themoviedb.org/3"
TRENDING = f"{BASE_URL}/trending/all/week?api_key={API_KEY}"
POSTER_PATH = "https://image.tmdb.org/t/p/w500"

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
    url = TRENDING
    trending = requests.get(url).json()
    return render_template('base.html', trending=trending)

@app.route('/movie/<int:movie_id>')
def movie_info(movie_id):
    url = f"{BASE_URL}/movie/{movie_id}?api_key={API_KEY}&language=en-US"
    movie_data = requests.get(url).json()
    return render_template('movie_info.html', movie_data=movie_data)

@app.route('/tv/<int:series_id>')
def series_info(series_id):
    url = f"{BASE_URL}/tv/{series_id}?api_key={API_KEY}&language=en-US"
    tv_data = requests.get(url).json()
    return render_template('tv_info.html', tv_data=tv_data)

@app.route('/search/multi/', methods=['POST', 'GET'])
def search():
    media_name = request.args.get('query')
    url = f"{BASE_URL}/search/multi?api_key={API_KEY}&query={media_name}&include_adult=true&language=en-US"
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
   


