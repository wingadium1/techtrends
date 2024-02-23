import sqlite3
import os
from flask import Flask, jsonify, json, render_template, request, url_for, redirect, flash
from werkzeug.exceptions import abort
import logging
import random
from flagsmith import Flagsmith
flagsmith = Flagsmith(environment_key="hPLFQzvrDFyjkCmqDfnurh")

# The method below triggers a network request
flags = flagsmith.get_environment_flags()

users = ["user01", "user02", "user03", "user04", "user05"];

# from app import db_connection_counter
db_connection_counter = 0
# Function to get a database connection.
# This function connects to database with the name `database.db`
def get_db_connection():
    global db_connection_counter
    try:
        # check if the database file is existing
        if os.path.exists("database.db"):
            connection = sqlite3.connect("database.db")
        else:
            raise RuntimeError('Database file is not initialized, please run python init_db.py!')
    except sqlite3.OperationalError:
        app.logger.error('Database.db file is not initialized. please run python init_db.py!')
    connection.row_factory = sqlite3.Row
    db_connection_counter += 1
    return connection

# Function to get a post using its ID
def get_post(post_id):
    connection = get_db_connection()
    post = connection.execute('SELECT * FROM posts WHERE id = ?',
                        (post_id,)).fetchone()
    connection.close()
    return post

# Define the Flask application
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your secret key'

# Define the main route of the web application
@app.route('/')
def index():
    connection = get_db_connection()
    posts = connection.execute('SELECT * FROM posts').fetchall()
    connection.close()
    return render_template('index.html', posts=posts)

# Define how each individual article is rendered
# If the post ID is not found a 404 page is shown
@app.route('/<int:post_id>')
def post(post_id):
    simulate_user = random.choice(users)
    identity_flags = flagsmith.get_identity_flags(identifier=simulate_user)
    # Check for feature error_page
    is_enabled_error_page = identity_flags.is_feature_enabled("error_page")
    post = get_post(post_id)
    if post is None:
        app.logger.error('Article with ID %s not found', post_id)
        if is_enabled_error_page:
          return render_template('error.html'), 500
        else:
          return render_template('404.html'), 404
    else:
        app.logger.info('Article "%s" retrieved!',post["title"])
        return render_template('post.html', post=post)

# Define the About Us page
@app.route('/about')
def about():
    app.logger.info("About us page!")
    return render_template('about.html')

# Define the post creation functionality
@app.route('/create', methods=['GET', 'POST'])
def create():
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']

        if not title:
            flash('Title is required!')
        else:
            connection = get_db_connection()
            connection.execute('INSERT INTO posts (title, content) VALUES (?, ?)',
                         (title, content))
            connection.commit()
            connection.close()

            app.logger.debug('Article %s created!',post["title"])
            return redirect(url_for('index'))

    return render_template('create.html')

@app.route('/healthz')
def healthz():
    try:
        connection = get_db_connection()
        connection.cursor()
        connection.execute("SELECT * FROM posts")
        connection.close()
        return jsonify(
            result='Ok - healthy'
        )
    except Exception:
        return jsonify(
            result='ERROR - unhealthy'
        ), 500

@app.route('/metrics')
def metrics():
    connection = get_db_connection()
    post_count = connection.execute('SELECT count(*) FROM posts').fetchone()[0]
    connection.close()
    return jsonify(
        db_connection_count=db_connection_counter,
        post_count=post_count
    )

def init_logger():
    log_level = os.getenv("LOGLEVEL", "DEBUG").upper()
    log_level = (
        getattr(logging, log_level)
        if log_level in ["CRITICAL", "DEBUG", "ERROR", "INFO", "WARNING",]
        else logging.DEBUG
    )

    logging.basicConfig(
        format='%(levelname)s:%(name)s:%(asctime)s, %(message)s',
                level=log_level,
    )

    logging.basicConfig(level=logging.DEBUG)

# start the application on port 3111
if __name__ == "__main__":
    init_logger()
    app.run(host='0.0.0.0', port='3111')
