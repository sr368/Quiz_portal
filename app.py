from flask import *
from flask_mysqldb import MySQL
import MySQLdb.cursors # Import configuration settings
import  re
import secrets
import os


app = Flask(__name__)
app.secret_key = '811027'
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'sreelekha'
app.config['MYSQL_DB'] ='quiz_portal'

mysql = MySQL(app)  # Load database settings from config.py

 # Create MySQL connection

# Teor Connecting to Database: {str(e)}"
@app.route('/')
def home():
    return render_template('home.html')
@app.route('/signup',methods=['POST','GET'])
def signup():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        
        

        # Validate email format
        if not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            flash("Invalid email format!", "danger")
            return redirect(url_for('signup'))

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # Check if email already exists
        cursor.execute("SELECT * FROM students WHERE email = %s", (email,))
        
        account = cursor.fetchone()
        
        if account:
            flash("Email already exists. Try another one.", "danger")
        else:
            passkey=secrets.token_hex(8)
            
            
            cursor.execute("INSERT INTO students (name, email, password,passkey) VALUES (%s, %s, %s,%s)", (name, email, password,passkey))
            mysql.connection.commit()
            flash("Signup successful! Please login.", "success")
            return render_template('signup.html',passkey=passkey)
            
        
        cursor.close()

    return render_template('signup.html',passkey=None)



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        print("raw form data ",request.form)
        email = request.form.get('email')
        password = request.form.get('password')
        print(email,password)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        # 1. Check in students table
        cursor.execute("SELECT * FROM students WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        role = "student" if user else None  

        # 2. If not found in students, check in admins table
        if not user:
            cursor.execute("SELECT * FROM admins WHERE email = %s", (email,))
            user = cursor.fetchone()
            role = "admin" if user else None  
            print("user fetched",user)

        cursor.close()
       

        # 3. If user found and password is correct, log them in
        if user  and user['password']==password:
            session['loggedin'] = True
            session['id'] = user['id']
            session['username'] = user['name']
            session['role'] = role  
            print(session)

            flash("Login successful!", "success")
            print("loggin success")

            # Redirect based on role
            if role == "student":
                return redirect(url_for('StudentDashboard'))
            elif role == "admin":
                return redirect(url_for('AdminDashboard'))
        else:
            flash("Incorrect email or password.", "danger")

    return render_template('login.html')

@app.route('/StudentDashboard')
def StudentDashboard():
    if 'loggedin' in session and session['role'] == 'student':
        return render_template('StudentDashboard.html',username=session['username'])
    else:
        flash("Unauthorized access!", "warning")
        return redirect(url_for('home'))

@app.route('/AdminDashboard')
def AdminDashboard():
    if 'loggedin' in session and session['role'] == 'admin':
        return render_template('AdminDashboard.html',username=session['username'])
    else:
        flash("Unauthorized access!", "warning")
        return redirect(url_for('home'))



@app.route('/password', methods=['GET', 'POST'])
def password():
    if request.method == 'POST':
        data = request.form

        if 'passkey' in data:  # Step 1: Passkey Verification
            passkey = data['passkey']
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT email FROM students WHERE passkey = %s", (passkey,))
            account = cursor.fetchone()

            if account:
                return jsonify({"status": "success", "email": account[0]})
            else:
                return jsonify({"status": "error", "message": "Invalid passkey. Try again."})

        elif 'new_password' in data:  # Step 2: Password Reset
            email = data['email']
            new_password = data['new_password']
            print(new_paasword,'sdffff')
            confirm_password = data['confirm_password']

            if new_password == confirm_password:
                cursor = mysql.connection.cursor()
                cursor.execute("UPDATE students SET password = %s WHERE email = %s", (new_password, email))
                mysql.connection.commit()
                return jsonify({"status": "success", "message": "Password reset successful! You can now log in."})
            else:
                return jsonify({"status": "error", "message": "Passwords do not match."})

    return render_template('password.html')  # Show the page initially
# Logout
# Route for Logout
@app.route('/logout',methods=['GET','POST'])
def logout():
    session.clear()  # Remove admin session
    flash("Logged out successfully", "success")
    return redirect(url_for('home')) 
@app.route('/quizze')
def show_quizzes():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT quiz_id, quiz_name FROM quizze")
    quizze = cursor.fetchone()
    return render_template('manage_quizzes.html', quizze=quizze)# Redirect to admin login
@app.route('/add_quiz', methods=['GET', 'POST'])
def add_quiz():
    if 'quiz_name' not in request.form:
        return "Error: Quiz name is missing!", 400  

    quiz_name = request.form['quiz_name'].strip()

    if not quiz_name:
        return "Error: Quiz name cannot be empty!", 400  

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Insert new quiz
    cursor.execute("INSERT INTO quizze (quiz_name) VALUES (%s)", (quiz_name,))
    mysql.connection.commit()

    # Fetch new quiz ID
    cursor.execute("SELECT LAST_INSERT_ID() AS quiz_id")
    result = cursor.fetchone()  # Fetch one row

    print("Fetched result:", result)  # Debugging

    cursor.close()

    if result is None:
        return "Error: No quiz ID returned!", 500  # Debugging step

    if 'quiz_id' not in result:
        return f"Error: Expected key 'quiz_id' not found! Available keys: {list(result.keys())}", 500  

    quiz_id = result['quiz_id']  # Correctly fetch the quiz_id

    return redirect(url_for('add_questions', quiz_id=quiz_id))
@app.route('/manage_quizzes')
def manage_quizzes():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM quizze")
    quizzes = cursor.fetchall()
    print(quizzes)
    return render_template('manage_quizzes.html', quizze=quizzes)
@app.route('/delete_quiz/<int:quiz_id>', methods=['POST'])
def delete_quiz(quiz_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM quizze WHERE quiz_id = %s", (quiz_id,))
    mysql.connection.commit()
    cursor.close()
    return redirect(url_for('manage_quizzes'))

# Route for adding questions
@app.route('/add_questions/<int:quiz_id>', methods=['GET', 'POST'])
def add_questions(quiz_id):
    if request.method == 'POST':
        question_text = request.form['question_text']#TCP provides reliable ,connection-oriented communication with error checking and correction.
        option1 = request.form['option_a']
        option2 = request.form['option_b']
        option3 = request.form['option_c']
        option4 = request.form['option_d']
        correct_option = request.form['correct_option']
        explanation = request.form['explanation']

        cursor = mysql.connection.cursor()
        cursor.execute(
            "INSERT INTO question (quiz_id, question_text, option_a, option_b, option_c, option_d, correct_option, explanation) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
            (quiz_id, question_text, option1, option2, option3, option4, correct_option, explanation)
        )
        mysql.connection.commit()
        cursor.close()

        return redirect(url_for('add_questions', quiz_id=quiz_id))

    return render_template('add_questions.html', quiz_id=quiz_id)

    
     # Send data as JSON
# Folder to store uploaded files
UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure the uploads folder exists
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)


@app.route('/upload_study_materials', methods=['GET', 'POST'])
def upload_study_materials():
    if request.method == 'POST':
        title = request.form['title']
        file = request.files['file']
        
        if file and title:
            filename = file.filename
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            
            cursor = mysql.connection.cursor()
            # Save file details in the database
            cursor.execute("INSERT INTO study_material (title, filename) VALUES (%s, %s)", (title, filename))
            mysql.connection.commit()
            

            return" FILE UPLOADED SUCCESSFULLY"
        else:
            return "Please enter a title and select a file."
    
    return render_template('upload_study_materials.html')

# Route to Display Available Quizzespython -m venv venv
@app.route('/Available_quizzes')
def Available_quizzes():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute("SELECT quiz_id, quiz_name FROM quizze")
    quizzes = cursor.fetchall()
    return render_template('Available_quizzes.html', quizze=quizzes)
@app.route('/view_students')
def view_students():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    query = """
    SELECT s.name, s.email, 
           q.quiz_name AS subject, 
           COALESCE(qa.score, 0) AS score
    FROM students s
    LEFT JOIN quiz_attempt qa ON s.email = qa.email
    LEFT JOIN quizze q ON qa.quiz_id = q.quiz_id
    ORDER BY s.name
    """

    cursor.execute(query)
    students = cursor.fetchall()
    cursor.close()

    return render_template('view_students.html', students=students)

# Route to Start a Specific Quiz
# Route to start quiz with selected quiz_id
@app.route('/start_quiz/<int:quiz_id>')
def start_quiz(quiz_id):
    
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM question WHERE quiz_id = %s", (quiz_id,))
    questions = cursor.fetchall()
    cursor.close()
    print(len(questions))
    return render_template('start_quiz.html', questions=questions, quiz_id=quiz_id)

@app.route('/submit_quiz/<int:quiz_id>', methods=['POST'])
def submit_quiz(quiz_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch correct questions for the given quiz_id
    cursor.execute("SELECT question_id, question_text, correct_option, explanation FROM question WHERE quiz_id = %s", (quiz_id,))
    questions = cursor.fetchall()

    # Convert to dictionary {question_id: question_data}
    question_dict = {str(q['question_id']): q for q in questions}  
    print("Available Question IDs:", question_dict.keys())  # Debugging Output

    # Create a mapping {q1: 40, q2: 41, ...} based on question order
    question_id_mapping = {f"q{index+1}": str(q['question_id']) for index, q in enumerate(questions)}
    print("Question ID Mapping:", question_id_mapping)  # Debugging Output

    total_score = 0
    wrong_answers = []

    # Process submitted answers
    for question_id, selected_answer in request.form.items():
        if question_id in ["quiz_id", "subject"]:
            continue  # Skip non-question fields

        # Convert q1, q2... to real question_id
        actual_question_id = question_id_mapping.get(question_id, question_id)
        print(f"Received question_id: {question_id} -> Actual ID: {actual_question_id}")  # Debugging output

        # Fetch the correct question data
        question = question_dict.get(actual_question_id)  
        print("Matched question:", question)  # Debugging output

        if question:
            correct_answer = question['correct_option']
            explanation = question['explanation']
            question_text = question['question_text']

            if selected_answer == correct_answer:
                total_score += 1  # 1 point per correct answer
            else:
                wrong_answers.append({
                    'question_text': question_text,
                    'selected_answer': selected_answer,
                    'correct_answer': correct_answer,
                    'explanation': explanation
                })
    student_id=session['id']            
    cursor.execute("SELECT * FROM students WHERE id= %s", (student_id,))
    p=cursor.fetchone()
    student_email = p['email']
    name=session['username']
    print(name)
              
    cursor.execute("SELECT * FROM quizze WHERE quiz_id= %s", (quiz_id,))
    s=cursor.fetchone()
    subject=s['quiz_name']
    from datetime import datetime
    c=datetime.now()
    
    print(c)
    # nsert or update the quiz_attempt table
    insert_query = """
        INSERT INTO quiz_attempt (email,student_id,name, quiz_id,subject, score, attempt_time,dates)
        VALUES (%s,%s, %s,%s, %s, %s,NOW(),%s)
        ON DUPLICATE KEY UPDATE score = VALUES(score), attempt_time = NOW()
    """
    cursor.execute(insert_query, (student_email,student_id,name,quiz_id,subject, total_score,c))            

    mysql.connection.commit()
    cursor.close()

    return render_template('submit_quiz.html', total_score=total_score, wrong_answers=wrong_answers)
    


# Route to show study materials
@app.route('/view_study_material')
def view_study_material():
    files = os.listdir('uploads')
    print(files)
    materials = [{'filename': file} for file in files]
    return render_template('view_study_material.html', materials=materials)

# Route to handle file downloads
@app.route('/download/<path:filename>')
def download_file(filename):
    return send_from_directory('uploads', filename, as_attachment=True)




@app.route('/viewscore/')
def viewscore():
    student_id=session['id']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM students WHERE id= %s", (student_id,))
    p=cursor.fetchone()
    email = p['email']

    query = """
    SELECT q.quiz_name AS subject, qa.score, qa.dates
    FROM quiz_attempt qa
    JOIN quizze q ON qa.quiz_id = q.quiz_id
    WHERE qa.email = %s
    ORDER BY q.quiz_name
    """
    
    cursor.execute(query, (email,))
    scores = cursor.fetchall()
    cursor.close()

    return render_template('viewscore.html', scores=scores, email=email)


    #cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    #.execute("SELECT * FROM students  WHERE id = %s", (student_id,))
    #questions = cursor.fetchone()
    #student_email=questions['email']# Fetch email from session



@app.route('/download_score/<email>/<subject>')
def download_score(email, subject):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    query = """
    SELECT s.name, s.email, q.quiz_name AS subject, qa.score
    FROM students s
    JOIN quiz_attempt qa ON s.email = qa.email
    JOIN quizze q ON qa.quiz_id = q.quiz_id
    WHERE s.email = %s AND q.quiz_name = %s
    """

    cursor.execute(query, (email, subject))
    result = cursor.fetchone()
    cursor.close()

    if not result:
        return f"No score found for {subject}", 404

    scorecard_text = f"""Name: {result['name']}
Email: {result['email']}
Subject: {result['subject']}
Score: {result['score']}"""

    filename = f"scorecard_{result['subject']}_{result['email']}.txt"

    return Response(scorecard_text, mimetype="text/plain",
                    headers={"Content-Disposition": f"attachment; filename={filename}"})


if __name__ == '__main__':
    app.run(debug=True)