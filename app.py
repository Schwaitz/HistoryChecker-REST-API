from flask import Flask, request, abort, jsonify, render_template
from flask_mysqldb import MySQL
from datetime import datetime
import requests

import mysql_config as mysql_config

app = Flask(__name__)

app.config['TESTING'] = True
app.config['SECRET_KEY'] = b'Sk\xad\xafd\x1f\x10\x9f\xb2\xd9\x9ea\xednx\x83'

app.config['MYSQL_HOST'] = mysql_config.host
app.config['MYSQL_USER'] = mysql_config.user
app.config['MYSQL_PASSWORD'] = mysql_config.password
app.config['MYSQL_DB'] = mysql_config.database
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

app.url_map.strict_slashes = False

mysql = MySQL(app)


def get_found():
    return requests.get("http://schwaitz.com:8080/data/found.json").json()


def get_found_lower():
    return dict((k.lower(), v) for k, v in get_found().items())


def user_in_found(username):
    return username.lower() in get_found_lower()


def subreddit_in_found(name):
    for (k, v) in get_found_lower():
        if v["subreddit"] == name.lower():
            return True

    return False


def make_error(message):
    return jsonify({
        'status': 'fail',
        'message': message
    })


def timestamp():
    return str(datetime.today().strftime("%m/%d/%Y %H:%M:%S %p"))


def execute_select(query, values=('none',)):
    cur = mysql.connection.cursor()
    try:
        if values[0] == 'none':
            cur.execute(query)
        else:
            cur.execute(query, values)

        data = list(cur.fetchall())
        if len(data) == 1:
            data = data[0]
        cur.close()

    except Exception as e:
        data = {'status': 'error', 'data': {'action': 'SELECT', 'exception': str(type(e).__name__), 'message': 'Error during execution of query'}}
    finally:
        cur.close()

    return data


def user_exists(name):
    data = execute_select("""SELECT COUNT(*) FROM users WHERE username = %s""", (name,))
    return data["COUNT(*)"] >= 1


def get_all_data():
    data = execute_select("""SELECT * FROM users""")

    fixed_data = {}
    for u in data:
        fixed_data[u['username']] = {'subreddit': u['subreddit'], 'type': u['type'], 'content': u['content'], 'date': u['date']}

    return_data = {'status': 'success', 'data': fixed_data}
    return return_data


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/users', methods=['GET', 'POST'])
def users():
    if request.method == 'GET':
        return jsonify(get_all_data())

    elif request.method == 'POST':
        if not user_exists(request.form['username']):
            cur = mysql.connection.cursor()
            now_timestamp = timestamp()
            return_message = {}
            try:
                cur.execute("""INSERT INTO users (username, subreddit, type, content, date) VALUES (%s, %s, %s, %s, %s)""",
                            (request.form['username'], request.form["subreddit"], request.form["type"], request.form["content"].encode('unicode_escape'), now_timestamp))
                mysql.connection.commit()
                cur.close()
                return_message = jsonify({
                    'status': 'success', 'action': 'INSERT',
                    'data': {'username': request.form['username'], 'subreddit': request.form["subreddit"], 'type': request.form["type"], 'content': request.form["content"], 'date': now_timestamp}
                })
            except Exception as e:
                return_message = jsonify({'status': 'error', 'action': 'INSERT', 'exception': str(type(e).__name__), 'message': 'Error during execution of query'})
            finally:
                cur.close()
                return return_message

        else:
            return make_error("User already exists")

    else:
        return make_error("Invalid HTTP Method")


@app.route('/users/<username>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def user(username):
    if request.method == 'GET':
        if user_exists(username):
            cur = mysql.connection.cursor()
            data = execute_select("""SELECT * FROM users WHERE username = %s""", (username,))

            return_data = {'status': 'success', 'data': data}
            return jsonify(return_data)
        else:
            return make_error("User does not exist")

    elif request.method == 'PUT':
        if request.form['subreddit'] != '' and request.form['type'] != '' and request.form['content'] != '':
            if user_exists(username):
                now_timestamp = timestamp()
                cur = mysql.connection.cursor()
                return_message = {}
                try:
                    cur.execute("""UPDATE users SET subreddit = %s, type = %s, content = %s, date = %s WHERE username = %s""",
                                (request.form['subreddit'], request.form['type'], request.form['content'], now_timestamp, username))
                    mysql.connection.commit()

                    return_message = jsonify({
                        'status': 'success', 'action': 'UPDATE',
                        'data': {'username': request.form['username'], 'subreddit': request.form["subreddit"], 'type': request.form["type"], 'content': request.form["content"], 'date': now_timestamp}
                    })
                except Exception as e:
                    return_message = jsonify({'status': 'error', 'action': 'UPDATE', 'exception': str(type(e).__name__), 'message': 'Error during execution of query'})
                finally:
                    cur.close()
                    return return_message

            else:
                return make_error("User does not exist")
        else:
            return make_error("Missing fields")


    elif request.method == 'DELETE':
        if user_exists(username):
            cur = mysql.connection.cursor()

            try:
                cur.execute("""DELETE FROM users WHERE username = %s""", (username,))
                mysql.connection.commit()

                return_message = jsonify({'status': 'success', 'action': 'DELETE'})
            except Exception as e:
                return_message = jsonify({'status': 'error', 'action': 'DELETE', 'exception': str(type(e).__name__), 'message': 'Error during execution of query'})
            finally:
                cur.close()

            return return_message

        else:
            return make_error("User does not exist")

    else:
        return make_error("Invalid HTTP Method")


@app.route('/subreddits')
def subreddits():
    data = get_all_data()["data"]

    subreddit_data = {}
    for (k, v) in data.items():
        subreddit_data[v["subreddit"]] = subreddit_data.get(v["subreddit"], [])
        subreddit_data[v["subreddit"]].append(k)

    return_data = {'status': 'success', 'data': subreddit_data}
    return jsonify(return_data)


@app.route('/subreddits/<name>')
def subreddit(name):
    data = get_all_data()["data"]

    user_list = []
    for (k, v) in data.items():
        if v["subreddit"].lower() == name.lower():
            user_list.append(k)

    return_data = {'status': 'success', 'data': {'name': name, 'count': len(user_list), 'users': user_list}}
    return jsonify(return_data)


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=False)
