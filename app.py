from flask import Flask, request, render_template, session, flash, redirect, url_for
from flask_bootstrap import Bootstrap
from flaskext.mysql import MySQL
from flask_session import Session
from flask_ckeditor import CKEditor
import yaml
import os
import datetime
from flask import send_from_directory
# from whoosh.analysis import StemmingAnalyzer
# import flask_whooshalchemy

# initial global parameters
mysql = MySQL()
application = app = Flask(__name__)
db = yaml.load(open('./config/db.yaml'))
mysql.init_app(app)
Bootstrap(app)

# config db parameters
app.config['MYSQL_DATABASE_HOST'] = db['mysql_host']
app.config['MYSQL_DATABASE_PORT'] = db['mysql_port']
app.config['MYSQL_DATABASE_USER'] = db['mysql_user']
app.config['MYSQL_DATABASE_PASSWORD'] = db['mysql_password']
app.config['MYSQL_DATABASE_DB'] = db['mysql_db']
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'


@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/', methods=['POST', 'GET'])
def index():
    # login and show the task list
    if "username" in session:
        sql = "SELECT t.LIST_ID, t.LIST_TITLE, t.LIST_STATUS, t.LIST_DUEDATE, u.USER_NAME FROM todolist as t "\
            "LEFT JOIN user as u ON t.LIST_USERID = u.USER_ID WHERE u.USER_ID = '" + \
            session['user_id'] + "'"
        print(sql)
        cnn = mysql.connect()
        cur = cnn.cursor()
        resultValue = cur.execute(sql)
        if resultValue > 0:
            tasklist = cur.fetchall()
            cur.close()
            return render_template("tasklist.html", tasklist=tasklist)
        else:
            flash('Create your first task!')
            return render_template("tasklist.html", tasklist="")

    return render_template("index.html")


@app.route('/logout')
def logout():
    # remove teh username from teh session if it is their
    session.pop('username', None)
    return redirect(url_for('index'))


@app.route('/tasklist/<string:category>/', methods=['POST', 'GET'])
def tasklist(category):

    if request.method == "GET":
        sql = ""
        # login and show the task list
        if category == "all":
            sql = "SELECT t.LIST_ID, t.LIST_TITLE, t.LIST_STATUS, t.LIST_DUEDATE, u.USER_NAME FROM todolist as t "\
                "LEFT JOIN user as u ON t.LIST_USERID = u.USER_ID " \
                "WHERE u.USER_ID = '" + session['user_id'] + "'"
        else:
            sql = "SELECT t.LIST_ID, t.LIST_TITLE, t.LIST_STATUS, t.LIST_DUEDATE, u.USER_NAME FROM todolist as t LEFT JOIN user as u " \
                "ON t.LIST_USERID = u.USER_ID WHERE t.LIST_STATUS = '" + \
                category + "' AND u.USER_ID = '" + session['user_id'] + "'"

    if request.method == "POST":
        if category == "search":
            _tasksearch = request.form['txttasksearch']
            sql = "SELECT t.LIST_ID, t.LIST_TITLE, t.LIST_STATUS, t.LIST_DUEDATE, u.USER_NAME FROM todolist as t LEFT JOIN user as u " \
                "ON t.LIST_USERID = u.USER_ID WHERE t.LIST_TITLE = '%" + \
                _tasksearch + "%' AND u.USER_ID = '" + session['user_id'] + "'"

    print(sql)
    cnn = mysql.connect()
    cur = cnn.cursor()
    resultValue = cur.execute(sql)
    if resultValue > 0:
        tasklist = cur.fetchall()
        cur.close()
        # return url_for('tasklist')
        return render_template('tasklist.html', tasklist=tasklist)
    cur.close()
    return render_template('tasklist.html')


@app.route('/addtask', methods=['POST', 'GET'])
def addtask():
    conn = mysql.connect()
    cur = conn.cursor()
    if request.method == 'POST':
        _title = request.form['taskTitle']
        _duedate = request.form['txtTaskDueDate']
        _description = request.form['txtTestDesc']
        _comment = request.form['txtComment']
        _user_id = session['user_id']
        cur.callproc('sp_addnewTask', (_title, _duedate,
                                       _description, _comment, _user_id))
        returnData = cur.fetchall()
        if len(returnData) is 0:
            conn.commit()
            cur.close()
            conn.close()
            print("successful")
            flash('Create the Task successfully')
            return redirect('tasklist')
    cur.close()
    conn.close()
    return render_template('addtask.html')


@app.route('/updatetask/<string:task_id>', methods=['POST', 'GET'])
def updatetask(task_id):

    conn = mysql.connect()
    cur = conn.cursor()
    # select the spicific task and ready to update
    if request.method == 'GET':
        sql = "SELECT LIST_TITLE, LIST_STATUS, LIST_DESCRIPTION, LIST_LOG, LIST_DUEDATE, LIST_ID FROM todolist WHERE LIST_ID = '" + task_id + "'"
        resultdata = cur.execute(sql)
        if resultdata > 0:
            task = cur.fetchall()
            cur.close()
            return render_template('updatetask.html', task=task)
    if request.method == 'POST':
        _duedate = request.form['txtTaskDueDate']
        _status = request.form['selTaskSelected']
        # _taskDesc     = request.form['txtTestDesc']
        _taskComment = request.form['txtComment']
        cur.callproc('sp_updateTask', (_taskComment,
                                       _duedate, _status, task_id))
        returnData = cur.fetchall()
        if len(returnData) is 0:
            conn.commit()
            cur.close()
            conn.close()
            print("update task successful")
            return redirect('/tasklist/' + _status)

    return redirect('/')


@app.route('/sharetask/<string:task_id>/<string:task_name>', methods=['POST', 'GET'])
def sharetask(task_id, task_name):
    conn = mysql.connect()
    cur = conn.cursor()
    if (request.method == 'POST'):
        _sharedpeople = request.form['sharingToPeople']
        print(_sharedpeople)
        cur.callproc('sp_shareTask', (task_id, _sharedpeople))
        returndata = cur.fetchall()
        if len(returndata) is 1:
            conn.commit()
            cur.close()
            conn.close()
            print('share successful')
            flash('Share successfully')
            return render_template('sharetask.html')
    return render_template('sharetask.html', task_id=task_id, task_name=task_name)


@app.route('/signin', methods=['POST'])  # login
def signin():
    # try:
    _name = request.form['txtUsername']
    _password = request.form['txtPassword']

    conn = mysql.connect()
    cursor = conn.cursor()
    if _name and _password:
        args = (_name, _password)
        cursor.callproc('sp_verifyUserAccount', args)
        returnData = cursor.fetchall()
        if len(returnData) is 1:
            conn.commit()
            cursor.close()
            conn.close()
            session['username'] = _name  # has some problem
            session['user_id'] = returnData[0][0]
            return redirect('/')
        else:
            return render_template("signup.html")
    return redirect('/')


@app.route('/deletetask/<string:task_id>', methods=['POST', 'GET'])
def deletetask(task_id):
    conn = mysql.connect()
    cur = conn.cursor()
    if request.method == 'GET':
        sql = "Delete from todolist Where LIST_ID = '" + task_id + "'"
        cur.execute(sql)
        returnData = cur.fetchall()
        if len(returnData) is 0:
            conn.commit()
            cur.close()
            conn.close()
            # flash('Delete succefully')
            return redirect('/tasklist/all')
    return redirect('/')


@app.route('/signup', methods=['POST', 'GET'])  # create user
def signup():
    # read the post value from UI
    if request.method == 'POST':
        _name = request.form['inputName']
        _password = request.form['inputPassword']
        _email = request.form['inputEmail']
        # vaildate if input all three item
        if _name and _password and _email:
            conn = mysql.connect()
            cursor = conn.cursor()
            # _hash_password = werkzeug.security.generate_password_hash(_password)
            cursor.callproc('sp_createNewUser', (_name, _password, _email))
            returnData = cursor.fetchall()
            print(returnData)
            if len(returnData) is 0:
                conn.commit()
                cursor.close()
                conn.close()
            return redirect('/')
    return render_template('signup.html')


if __name__ == "__main__":
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SECRET_KEY'] = b'_5#y2L"F4Q8z\n\xec]/'

    mysess = Session()
    mysess.init_app(app)
    app.run()
