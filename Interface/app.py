import pickle
import joblib
from datetime import datetime
import pandas as pd 
import sqlite3
import warnings
from flask_sqlalchemy import SQLAlchemy
from flask import Flask, render_template, request, redirect, url_for, flash , session

warnings.filterwarnings('ignore')

app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Required for session management

# Configure SQLite database
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Load the stroke prediction model
model = joblib.load("stroke_model.pkl")

# Check the type of the loaded model
print("Loaded model type:", type(model))

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(),nullable=False)

    # Relationship to StrokeInput
    stroke_inputs = db.relationship('StrokeInput', backref='users', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'
    
class Contact(db.Model):
    __tablename__ = 'contact'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String)
    message = db.Column(db.String)
    name = db.Column(db.String)

    def __repr__(self):
        return f'<Contact id={self.id} email={self.email}>' 

class StrokeInput(db.Model):
    __tablename__ = 'stroke_inputs'
    id = db.Column(db.Integer, primary_key=True)
    age = db.Column(db.Float, nullable=False)
    hypertension = db.Column(db.Boolean, nullable=False)
    heart_disease = db.Column(db.Boolean, nullable=False)
    avg_glucose = db.Column(db.Float, nullable=False)
    bmi = db.Column(db.Float, nullable=False)
    smoking_status = db.Column(db.String(50), nullable=False)
    marital_status = db.Column(db.String(50), nullable=False)
    work_type = db.Column(db.String(50), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    stroke_prediction = db.Column(db.String(20))
    stroke_percentage = db.Column(db.String(20))
    gender = db.Column(db.String())
    # Foreign key linking to the User table
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    def __repr__(self):
        return f'<StrokeInput ID {self.id}, User {self.user_id}>'


# # Initialize the SQLite database
# def init_db():
#     conn = sqlite3.connect('users.db')
#     cursor = conn.cursor()
#     cursor.execute('''
#         CREATE TABLE IF NOT EXISTS users (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             username TEXT UNIQUE NOT NULL,
#             password TEXT NOT NULL
#         )
#     ''')
#     conn.commit()
#     conn.close()

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

        # Get user_id from session
        user_id = session.get('user_id')

        if user_id:
            # Create a new StrokeInput record linked to the logged-in user
            new_stroke_input = StrokeInput(
                age=age,
                hypertension=hypertension_value,
                heart_disease=heart_disease_value,
                avg_glucose=avg_glucose,
                bmi=bmi,
                smoking_status=smoking_status,
                marital_status=marital_status,
                work_type=work_type,
                stroke_prediction = stroke_prediction,
                stroke_percentage = stroke_percentage,
                user_id=user_id,  # Link the input data to the logged-in user
                gender=gender
            )

            # Save the new StrokeInput to the database
            try:
                db.session.add(new_stroke_input)
                db.session.commit()
            except Exception as e:
                db.session.rollback()  # Rollback in case of an error
                flash(f"Error saving stroke input: {e}", "danger")

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
                               stroke_percentage=stroke_percentage)

    return render_template('input.html')


@app.route('/input/explain') #explain variables
def explain():
    return render_template('explain.html')

#Login Page
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.password == password:  # Replace with hashed password for security
            session['user_id'] = user.id  # Store user ID in the session
            session['username'] = user.username  # Store username in the session
            return redirect(url_for('account'))
        else:
            return redirect(url_for('login_error'))
            #flash('Invalid username or password', 'danger')

    return render_template('login.html')

#Login Not Ok
@app.route('/login/error')
def login_error():
    message = request.args.get('message', "An unknown error occurred.")
    return render_template('login_error.html', message=message)

# Signup page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']

        new_user = User(username=username, password=password, email = email)
        try:
            db.session.add(new_user)  # Add the user to the data    base session
            db.session.commit()  # Commit the transaction
            return redirect(url_for('signup_success'))
        except Exception as e:
            db.session.rollback()  # Rollback the transaction if there's an error
            error_message = str(e)
            return redirect(url_for('signup_error',message=error_message))

    return render_template('signup.html')

@app.route('/signup/error')
def signup_error():
    message = request.args.get('message', "An unknown error occurred.")
    return render_template('signup_error.html', message=message)

@app.route('/signup/success')
def signup_success():
    return render_template('signup_success.html')  # This is the success page

@app.route('/account')
def account():
    # Retrieve user ID from the session
    user_id = session.get('user_id')
    
    if user_id: 
        user = User.query.get(user_id)  # Fetch the user from the database using the user_id
        if user:
            stroke_inputs = StrokeInput.query.filter_by(user_id=user_id).all()
            return render_template('account.html', user=user,stroke_inputs=stroke_inputs)  # Pass the user to the template
        else:
            flash("User not found", "danger")
            return redirect(url_for('login'))
    else:
        return redirect(url_for('login'))  # Redirect to login if no user is found in session


@app.route('/logout')
def logout():
    # Clear the session or token that tracks the user login
    session.clear()  # or another logout method depending on your implementation
    return redirect(url_for('home'))  # Redirect to login page after logout

# About Us page
@app.route('/about')
def about():
    return render_template('about.html')

# Information page
@app.route('/info')
def info():
    return render_template('info.html')

# Contact Us page
@app.route('/contact', methods = ['GET', 'POST'])
def contact():
    if request.method == 'POST':
        # Retrieve data from the frontend
        name = request.form.get('name')
        message = request.form.get('message')
        email = request.form.get('email')

        add_contact = Contact(name=name, message=message, email=email)
        try:
            db.session.add(add_contact)  # Add the user to the database session
            db.session.commit()  # Commit the transaction
            return redirect(url_for('contact_success'))
        except Exception as e:
            db.session.rollback()  # Rollback the transaction if there's an error
            return f"Error: {e}"

    return render_template('contact.html')

@app.route('/contact/success')
def contact_success():
    return render_template('contact_success.html')  # This is the success page


# Run the Flask app
if __name__ == '__main__':
    with app.app_context():
        #db.drop_all() #Remove all the table saved before just delete the #
        db.create_all()  # Creates all tables defined in your models

    app.run(debug=True)