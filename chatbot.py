HEAD
from flask import Flask, render_template, request, redirect, url_for, session
import csv

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Dummy users
users = {'test@example.com': '1234'}

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email in users and users[email] == password:
            session['user'] = email
            return redirect('/chatbot')
        else:
            return "Invalid credentials"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        users[email] = password
        return redirect('/login')
    return render_template('register.html')

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    response = ""
    if request.method == 'POST':
        symptom = request.form['symptom'].lower()
        with open('chatbot_data.csv') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['symptom'].lower() == symptom:
                    response = f"Diagnosis: {row['diagnosis']}<br>Solution: {row['solution']}<br>Doctor: {row['doctor']}"
                    break
            else:
                response = "Sorry, I couldn't find that symptom."
    return render_template('chatbot.html', response=response)

if __name__ == '__main__':
    app.run(debug=True)
=======
from flask import Flask, render_template, request, redirect, url_for, session
import csv

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Dummy users
users = {'test@example.com': '1234'}

@app.route('/')
def welcome():
    return render_template('welcome.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        if email in users and users[email] == password:
            session['user'] = email
            return redirect('/chatbot')
        else:
            return "Invalid credentials"
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        users[email] = password
        return redirect('/login')
    return render_template('register.html')

@app.route('/chatbot', methods=['GET', 'POST'])
def chatbot():
    response = ""
    if request.method == 'POST':
        symptom = request.form['symptom'].lower()
        with open('chatbot_data.csv') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['symptom'].lower() == symptom:
                    response = f"Diagnosis: {row['diagnosis']}<br>Solution: {row['solution']}<br>Doctor: {row['doctor']}"
                    break
            else:
                response = "Sorry, I couldn't find that symptom."
    return render_template('chatbot.html', response=response)

if __name__ == '__main__':
    app.run(debug=True)
f35ef1c (Add Procfile and updated files for render deployment)
