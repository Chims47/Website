import pickle
from flask import Flask, render_template, request, redirect, url_for, flash
import joblib
import pandas as pd
import sqlite3
import warnings

warnings.filterwarnings('ignore')

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management

# Load the stroke prediction model
model = joblib.load("stroke_model.pkl")

# Check the type of the loaded model
print("Loaded model type:", type(model))

# Initialize the SQLite database
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

# Home page
@app.route('/')
def home():
    return render_template('home.html')

# Input page where users submit medical details
@app.route('/input', methods=['GET', 'POST'])
def input():
    if request.method == 'POST':
        # Retrieve form data (same as before)
        name = request.form.get('name')
        age = float(request.form.get('age'))
        gender = request.form.get('gender')

        # Convert hypertension and heart disease responses to numerical values
        hypertension_value = 1 if request.form.get('hypertension') == 'yes' else 0
        heart_disease_value = 1 if request.form.get('heart_disease') == 'yes' else 0

        # Retrieve other form data
        avg_glucose = float(request.form.get('avg_glucose'))
        bmi = float(request.form.get('bmi'))
        marital_status = request.form.get('marital_status')
        residence_type = request.form.get('residence_type')
        smoking_status = request.form.get('smoking_status')
        work_type = request.form.get('work_type')

        # Prepare input data for prediction
        input_data = [[age, hypertension_value, heart_disease_value, avg_glucose, bmi, smoking_status, marital_status, work_type]]
        columns = ['AGE', 'HYPERTENSION', 'HEART_DISEASE', 'AVG_GLUECOSE_LEVEL', 'BMI', 'SMOKING_STATUS', 'MARITAL_STATUS', 'WORK_TYPE']
        input_df = pd.DataFrame(input_data, columns=columns)

        # Print input data for debugging
        print("Input Data for Prediction:", input_data)

        # Predict using the model (get probability)
        try:
            # Use predict_proba to get the probability of stroke (class 1)
            prob = model.predict_proba(input_df)  # Returns probabilities for both classes
            stroke_probability = prob[0][1]  # The probability of stroke (class 1)
            stroke_percentage = stroke_probability * 100  # Convert to percentage
            stroke_prediction = 'Yes' if stroke_probability >= 0.5 else 'No'  # Threshold to decide stroke occurrence

        except Exception as e:
            print("Error during prediction:", e)
            stroke_prediction = f"Error in prediction: {e}"
            stroke_percentage = None  # In case of error, don't show percentage

        # Pass the collected data and prediction to the result page
        return render_template('result.html',
                               name=name,
                               age=age,
                               gender=gender,
                               hypertension=hypertension_value,
                               heart_disease=heart_disease_value,
                               avg_glucose=avg_glucose,
                               bmi=bmi,
                               marital_status=marital_status,
                               residence_type=residence_type,
                               smoking_status=smoking_status,
                               work_type=work_type,
                               stroke_prediction=stroke_prediction,
                               stroke_percentage=stroke_percentage)  # Add the percentage to the result page

    return render_template('input.html')

# Login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM users WHERE username = ?', (username,))
        user = cursor.fetchone()
        conn.close()

        if user and user[0] == password:  # In a real app, use hashed passwords
            return redirect(url_for('home'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')

# Signup page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        try:
            cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
            conn.commit()
            flash('Signup successful! You can now log in.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Username already exists. Please choose another one.', 'danger')
        finally:
            conn.close()

    return render_template('signup.html')

# About Us page
@app.route('/about')
def about():
    return render_template('about.html')

# Information page
@app.route('/info')
def info():
    return render_template('info.html')

# Contact Us page
@app.route('/contact')
def contact():
    return render_template('contact.html')

# Run the Flask app
if __name__ == '__main__':
    init_db()  # Initialize the database
    app.run(debug=True)