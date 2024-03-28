import os
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from pymongo import MongoClient
import pymongo
import bcrypt
import secrets

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)

client = MongoClient(os.environ.get('mongodb+srv://vishnulucky94414:yJIsBtfdZdtiPLLP@cluster0.hf5lz.mongodb.net/'))
db = client['mypro']
users_collection = db['users']
transactions_collection = db['transactions']

@app.route('/')
def index():
    if 'username' in session:
        return redirect(url_for('home'))
    return render_template('vis.html')

@app.route('/home')
def home():
    if 'username' in session:
        username = session['username']
        user = users_collection.find_one({'username': username})
        if user:
            balance = user.get('balance', 100)
            transactions = get_transactions(username)
            return render_template('index.html', username=username, balance=balance, transactions=transactions)

    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        existing_user = users_collection.find_one({'username': request.form['username']})

        if existing_user is None:
            hashpass = bcrypt.hashpw(request.form['password'].encode('utf-8'), bcrypt.gensalt())
            users_collection.insert_one({'username': request.form['username'], 'password': hashpass, 'balance': 0})
            session['username'] = request.form['username']
            flash('Signup successful!', 'success')
            return redirect(url_for('home'))

        flash('That username already exists!', 'error')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        existing_user = users_collection.find_one({'username': request.form['username']})

        if existing_user:
            if bcrypt.checkpw(request.form['password'].encode('utf-8'), existing_user['password']):
                session['username'] = request.form['username']
                return redirect(url_for('home'))
            else:
                return render_template('login.html', alert=True)

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

@app.route('/transfer', methods=['POST'])
def transfer():
    sender_username = session['username']
    recipient_username = request.form['recipient']
    amount = float(request.form['amount'])

    sender = users_collection.find_one({'username': sender_username})
    recipient = users_collection.find_one({'username': recipient_username})

    if sender and recipient:
        if sender['balance'] >= amount:
            sender_new_balance = sender['balance'] - amount
            recipient_new_balance = recipient['balance'] + amount

            users_collection.update_one({'username': sender_username}, {'$set': {'balance': sender_new_balance}})
            users_collection.update_one({'username': recipient_username}, {'$set': {'balance': recipient_new_balance}})

            # Save transaction details
            transaction = {
                'sender': sender_username,
                'recipient': recipient_username,
                'amount': amount,
                'timestamp': datetime.datetime.now()
            }
            transactions_collection.insert_one(transaction)

            flash('Transfer successful!', 'success')
        else:
            flash('Insufficient balance!', 'error')
    else:
        flash('User not found!', 'error')

    return redirect(url_for('home'))


@app.route('/deposit', methods=['POST'])
def deposit():
    if 'username' in session:
        username = session['username']
        amount = float(request.form['amount'])

        user = users_collection.find_one({'username': username})

        if user:
            new_balance = user['balance'] + amount
            users_collection.update_one({'username': username}, {'$set': {'balance': new_balance}})

            # Save deposit transaction details
            transaction = {
                'sender': username,
                'recipient': username,
                'amount': amount,
                'timestamp': datetime.datetime.now()
            }
            transactions_collection.insert_one(transaction)

            flash('Deposit successful!', 'success')
        else:
            flash('User not found!', 'error')
    else:
        flash('Please log in to deposit funds!', 'error')

    return redirect(url_for('home'))


def get_transactions(username):
    transactions = transactions_collection.find({'$or': [{'sender': username}, {'recipient': username}]})
    return transactions


