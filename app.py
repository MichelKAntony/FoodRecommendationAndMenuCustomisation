from flask import Flask, request, render_template, redirect, url_for, session
from flask_mysqldb import MySQL
import MySQLdb.cursors
import re
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

app = Flask(__name__)

app.secret_key = 'your secret key'
 
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Michel2002@'
app.config['MYSQL_DB'] = 'miniproject'
 
mysql = MySQL(app)
df = pd.read_csv('food_data.csv')
average_reviews = {}
@app.route('/')
@app.route('/login', methods =['GET', 'POST'])
def login():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form:
        username = request.form['username']
        password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = % s AND password = % s', (username, password, ))
        account = cursor.fetchone()
        if account:
            session['loggedin'] = True
            session['id'] = account['id']
            session['username'] = account['username']
            msg = 'Logged in successfully !'
            return render_template('index.html', msg = msg)
        else:
            msg = 'Incorrect username / password !'
    return render_template('login.html', msg = msg)
 
@app.route('/logout')
def logout():
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/recommend')
def recommend():
    return render_template('recommend.html')



 
@app.route('/register', methods =['GET', 'POST'])
def register():
    msg = ''
    if request.method == 'POST' and 'username' in request.form and 'password' in request.form and 'email' in request.form :
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM accounts WHERE username = % s', (username, ))
        account = cursor.fetchone()
        if account:
            msg = 'Account already exists !'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address !'
        elif not re.match(r'[A-Za-z0-9]+', username):
            msg = 'Username must contain only characters and numbers !'
        elif not username or not password or not email:
            msg = 'Please fill out the form !'
        else:
            cursor.execute('INSERT INTO accounts VALUES (NULL, % s, % s, % s)', (username, password, email, ))
            mysql.connection.commit()
            msg = 'You have successfully registered !'
    elif request.method == 'POST':
        msg = 'Please fill out the form !'
    return render_template('register.html', msg = msg)


@app.route('/search', methods=['GET'])
def search():

        flavor_profile = request.args.get('flavor_profile').lower()
        course = request.args.get('course').lower()
        diet = request.args.get('diet').lower()

        df = pd.read_csv('food_data.csv')

        df['name'] = df['name'].str.lower()
        df['flavor_profile'] = df['flavor_profile'].str.lower()
        df['course'] = df['course'].str.lower()
        df['diet'] = df['diet'].str.lower()
        df['ingredients'] = df['ingredients'].str.lower()

        model = SentenceTransformer('bert-base-nli-mean-tokens')

        flavor_embeddings = model.encode(df['flavor_profile']).tolist()
        course_embeddings = model.encode(df['course']).tolist()

        flavor_similarity = cosine_similarity(flavor_embeddings)
        course_similarity = cosine_similarity(course_embeddings)

        def get_index(recipe_name):
          return df[df['name'] == recipe_name].index.values[0]

        def get_recipe(index):
            return df[df.index == index]["name"].values[0]

        def get_recipe_recommendations(flavor_profile, course, diet, num_recommendations=20):
            flavor_indices = np.argsort(flavor_similarity)[::-1]
            course_indices = np.argsort(course_similarity)[::-1]

     
            flavor_filtered_indices = df[df['flavor_profile'].isin([flavor_profile])].index

   
            course_filtered_indices = df[df['course'].isin([course])].index


            filtered_indices = df[df['diet'].isin([diet])].index

            combined_indices = list(set(flavor_filtered_indices) & set(course_filtered_indices) & set(filtered_indices))
            recommendations = [get_recipe(i) for i in combined_indices]

            return recommendations[:num_recommendations]

        recommendations = get_recipe_recommendations(flavor_profile, course, diet)

        if not recommendations:
            message = "No recommendations found."
            return render_template('results.html', message=message)
        else:
            return render_template('results.html', recommendations=recommendations)
        
def calculate_average_review(reviews):
    valid_reviews = [review for review in reviews if review is not None]
    if valid_reviews:
        return np.mean(valid_reviews)
    else:
        return 0
   

@app.route('/recipe/<recipe_name>', methods=['GET'])
def recipe(recipe_name):
    df = pd.read_csv('food_data.csv')
    df['name'] = df['name'].str.lower()
    df['flavor_profile'] = df['flavor_profile'].str.lower()
    df['ingredients'] = df['ingredients'].str.lower()

    # Find the row corresponding to the selected recipe
    recipe_row = df[df['name'] == recipe_name]

    # Retrieve the flavor profile of the selected recipe
    flavor_profile = recipe_row['flavor_profile'].values[0]

    # Retrieve the ingredients of the selected recipe
    ingredients = [ingredient.strip() for ingredient in recipe_row['ingredients'].values[0].split(',')]

    average_review = average_reviews.get(recipe_name, 0)
    
    return render_template('ingredients.html', recipe=recipe_name, ingredients=ingredients, flavor_profile=flavor_profile, average_review=average_review)



@app.route('/order', methods=['POST'])
def order():
    if 'loggedin' in session:
        user_id = int(session['id'])
        recipe_name = request.form['recipe_name']
        flavor_level = request.form['flavor_profile']
        milk = request.form.get('milk', '')
        maida = request.form.get('maida', '')
        sugar = request.form.get('sugar', '')
        preferences = request.form['preferences']
        #rating = request.form.get('rating')

        cursor = mysql.connection.cursor()
        cursor.execute(
            'INSERT INTO orders (user_id, food_name, flavor_level, milk, maida, sugar, preferences) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s)',
            (user_id, recipe_name, flavor_level, milk, maida, sugar, preferences)
        )
        mysql.connection.commit()

        #cursor.execute('SELECT review FROM orders WHERE user_id = %s AND food_name = %s', (user_id, recipe_name))
        #reviews = [row[0] for row in cursor.fetchall()]

        # Calculate the average review
        #average_reviews[recipe_name] = calculate_average_review(reviews)

        return redirect(url_for('order_successful'))
    else:
        return redirect(url_for('login'))

# ...


@app.route('/order_successful')
def order_successful():
    return render_template('order.html')

# ...

@app.route('/review', methods=['GET', 'POST'])
def review():
    if request.method == 'POST':
        # Handle the POST request for submitting the review
        rating = request.form.get('rating')
        
        if 'loggedin' in session:
            user_id = int(session['id'])
            recipe_name = request.form['recipe_name']
            
            cursor = mysql.connection.cursor()
            cursor.execute(
                'UPDATE orders '
                'SET review = %s '
                'WHERE user_id = %s AND food_name = %s',
                (rating, user_id, recipe_name)
            )
            mysql.connection.commit()
            
            # Redirect the user to the thank you page
            return redirect(url_for('submit_review'))
        else:
            # Handle the case when the user is not logged in
            return redirect(url_for('login'))
    else:
        # Handle the GET request for showing the review form
        return render_template('review.html')

# ...


@app.route('/submit_review', methods=['GET', 'POST'])
def submit_review():
    if request.method == 'POST':
        rating = request.form.get('rating')
        recipe_name = request.form.get('recipe_name')

        cursor = mysql.connection.cursor()
        cursor.execute('UPDATE orders SET review = %s WHERE food_name = %s', (rating, recipe_name))
        mysql.connection.commit()

        cursor.execute('SELECT review FROM orders WHERE food_name = %s', (recipe_name,))
        reviews = [row[0] for row in cursor.fetchall()]

        # Calculate the average review
        average_reviews[recipe_name] = calculate_average_review(reviews)

    return render_template('thank_you.html')



if __name__ == '__main__':
    app.run(debug=True)