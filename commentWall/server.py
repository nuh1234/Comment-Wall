from flask import Flask, render_template, request, redirect, session, flash
from mysqlconnection import connectToMySQL
import re
from flask_bcrypt import Bcrypt        

app = Flask(__name__)
bcrypt = Bcrypt(app) 

app.secret_key = 'ThisIsSecret'
regex = re.compile(r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)")

@app.route('/')
def renderIndex():
    if session.get('user_id'):
        return redirect('/commentWall')

    return render_template('index.html')

@app.route('/register', methods=['POST'])
def register():
    if session.get('user_id'):
        return redirect('/commentWall')

    email = request.form['email']

    if len(request.form['first_name']) < 2:
        flash("First name must be more than 2 characters", 'first_name')
    elif not request.form['first_name'].isalpha():
        flash("First Name must be only letters", 'first_name')

    elif len(request.form['last_name']) < 2:
        flash("Last name must be more than 2 characters", 'last_name')
    elif not request.form['last_name'].isalpha():
        flash("Last Name must be only letters", 'last_name')

    elif len(request.form['password']) < 8:
        flash("Password must be more than 8 characters", 'password')
    elif not request.form['password'] == request.form['confirm_password']:
        flash("Passwords do not match", 'confirm_password')
    elif len(email) < 1:
        flash("Email cannot be blank!", 'email')
    elif not regex.match(email):
        flash("Invalid Email Address!", 'email')
    else:
        mysql = connectToMySQL("Users")
        query = "SELECT * FROM accounts WHERE email = %(email)s;"
        data = {
            'email': email
        }
        emailExists = mysql.query_db(query, data)
        if emailExists:
            flash("Email already registered", 'email')
        else:
            pw_hash = bcrypt.generate_password_hash(request.form['password']) 
            mysql = connectToMySQL("Users")
            query = "INSERT INTO accounts (first_name, last_name, email, password, created_at, updated_at) VALUES (%(first_name)s, %(last_name)s, %(email)s, %(password)s, NOW(), NOW());"
            data = {
                'first_name': request.form['first_name'],
                'last_name':  request.form['last_name'],
                'email': request.form['email'],
                'password': pw_hash
            }
            newUserID = mysql.query_db(query, data)
            session['user_id'] = newUserID
            return redirect('/commentWall')

    return redirect('/')
@app.route('/login', methods=['POST'])
def login():
    if session.get('user_id'):
        return redirect('/commentWall')

    mysql = connectToMySQL("Users")
    query = "SELECT * FROM accounts WHERE email = %(email)s;"
    data = {
        'email': request.form['email']
    }
    result = mysql.query_db(query, data)
    if not result:
        flash("User not found", 'login_email')
    else:
        if bcrypt.check_password_hash(result[0]['password'], request.form['password']):
            session['user_id'] = result[0]['id']
            session['user_name'] = result[0]['first_name']
            return redirect('/commentWall')
        else:
            flash("You could not be logged in", 'login_password')
    return redirect('/')

@app.route('/commentWall')
def commentWall():
    if not session.get('user_id'):
        return redirect('/')

    mysql = connectToMySQL("Users")
    recievedQuery = "SELECT messages.id, messages.message, messages.created_at, accounts.first_name, accounts.last_name FROM messages JOIN accounts ON messages.sender_id = accounts.id WHERE messages.recipient_id = %(id)s ORDER BY messages.created_at desc;"
    otherUsersQuery = "SELECT * FROM accounts WHERE accounts.id <> %(id)s ORDER BY accounts.first_name asc;"
    messageCountQuery = "SELECT  COUNT(*) as count FROM messages WHERE messages.sender_id = %(id)s;"
    
    data = {
        'id': session['user_id']
    }

    recievedMessages = mysql.query_db(recievedQuery, data)
    other_users = mysql.query_db(otherUsersQuery, data)
    message_count = mysql.query_db(messageCountQuery, data)
    count = message_count[0]['count']
    if other_users and recievedMessages:
        return render_template('commentWall.html', messages=recievedMessages, recipients=other_users, user_name=session['user_name'], count=count)

    return redirect('/')

@app.route('/message', methods=['POST'])
def message():
    if not session.get('user_id'):
        return redirect('/')
    if len(request.form['message'].strip()) < 1:
        flash("You can't send empty messages, they have no meaning 🙄", 'message')
    mysql = connectToMySQL("Users")
    messageQuery = "INSERT INTO messages (message, sender_id, recipient_id, created_at, updated_at) VALUES (%(message)s, %(sender_id)s, %(recipient_id)s, NOW(), NOW());"
    data = {
        'message': request.form['message'].strip(),
        'sender_id': session['user_id'],
        'recipient_id': request.form['recipient_id']
    }

    inserted = mysql.query_db(messageQuery, data)
    if inserted:
        flash("Sent 📲", 'message')

    return redirect('/commentWall')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/remove/message/<message_id>')
def remove(message_id):
    mysql = connectToMySQL("Users")
    selectQuery = "SELECT * FROM messages WHERE messages.id = %(message_id)s AND messages.recipient_id = %(recipient_id)s;"
    data = {
        'message_id': message_id,
        'recipient_id': session['user_id']
    }
    found_message = mysql.query_db(selectQuery, data)

    if not found_message:
        return redirect('/danger')
    
    deleteQuery = "DELETE FROM messages WHERE messages.id = %(message_id)s AND messages.recipient_id = %(recipient_id)s;"
    delete_message = mysql.query_db(deleteQuery, data)
    return redirect('/commentWall')

@app.route('/danger')
def danger():
    flash("You do not own that message, we have recorded your IP Address", "delete_error")
    return render_template('/danger.html')

if __name__ == "__main__":
    app.run(debug=True)