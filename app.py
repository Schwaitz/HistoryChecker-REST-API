from flask import Flask, request, jsonify, render_template, json
from flask_mysqldb import MySQL
from datetime import datetime
import requests

import app_config as app_config

app = Flask(__name__)

app.config['TESTING'] = True
app.config['SECRET_KEY'] = app_config.SECRET_KEY

app.config['MYSQL_HOST'] = app_config.host
app.config['MYSQL_USER'] = app_config.user
app.config['MYSQL_PASSWORD'] = app_config.password
app.config['MYSQL_DB'] = app_config.database
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
    return jsonify({'status': 'fail', 'message': message})


def timestamp():
    return str(datetime.today().strftime("%m/%d/%Y %H:%M:%S %p"))


def execute_select(query, values=('none',)):
    cur = mysql.connection.cursor()
    return_message = {}
    try:
        if values[0] == 'none':
            cur.execute(query)
        else:
            cur.execute(query, values)

        return_message = list(cur.fetchall())
        if len(return_message) == 1:
            return_message = return_message[0]

    except Exception as e:
        return_message = {'status': 'error', 'data': {'action': 'SELECT', 'exception': str(type(e).__name__), 'message': 'Error during execution of query'}}
    finally:
        cur.close()
        return return_message


def execute_insert(table, fields, values):
    cur = mysql.connection.cursor()
    return_message = {}
    try:
        values_string = "("
        for v in values:
            values_string += "%s, "
        values_string = values_string[:-2]
        values_string += ")"

        fields_string = "("
        for f in fields:
            fields_string += f + ", "
        fields_string = fields_string[:-2]
        fields_string += ")"

        query = """INSERT INTO {} {} VALUES {}""".format(table, fields_string, values_string)

        cur.execute(query, values)
        mysql.connection.commit()
        return_message = {'status': 'success', 'action': 'INSERT', 'data': {}}

        for i in range(0, len(fields)):
            return_message['data'][fields[i]] = values[i]

    except Exception as e:
        return_message = {'status': 'error', 'action': 'INSERT', 'exception': str(type(e).__name__), 'message': 'Error during execution of query'}
    finally:
        cur.close()
        return return_message


def execute_delete(table, field, value):
    cur = mysql.connection.cursor()
    return_message = {}
    try:
        query = """DELETE FROM {} WHERE {} = %s""".format(table, field)
        cur.execute(query, (value,))
        mysql.connection.commit()

        return_message = {'status': 'success', 'action': 'DELETE'}
    except Exception as e:
        return_message = {'status': 'error', 'action': 'DELETE', 'exception': str(type(e).__name__), 'message': 'Error during execution of query'}
    finally:
        cur.close()
        return return_message


def subreddit_whitelist_exists(name):
    data = execute_select("""SELECT COUNT(*) FROM subreddit_whitelist WHERE subreddit = %s""", (name,))
    return data["COUNT(*)"] >= 1


def user_subreddit_whitelist_exists(name):
    data = execute_select("""SELECT COUNT(*) FROM user_subreddit_whitelist WHERE username = %s""", (name,))
    return data["COUNT(*)"] >= 1


def user_whitelist_exists(name):
    data = execute_select("""SELECT COUNT(*) FROM user_whitelist WHERE username = %s""", (name,))
    return data["COUNT(*)"] >= 1


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


def check_password(password):
    return password == app_config.edit_password


@app.route('/')
def index():
    endpoints = [
        {'methods': 'GET, POST', 'link': '/users', 'desc': 'data for all users'},
        {'methods': 'GET, PUT, DELETE', 'link': '/users/username', 'desc': 'data for a single user'},

        {'methods': 'GET', 'link': '/subreddits', 'desc': 'data for all subreddits'},
        {'methods': 'GET', 'link': '/subreddits/name', 'desc': 'data for a single subreddit'},

        {'methods': 'GET, POST', 'link': '/whitelist/subreddit', 'desc': 'data for all whitelisted subreddits'},
        {'methods': 'GET, DELETE', 'link': '/whitelist/subreddit/name', 'desc': 'data for a single whitelisted subreddit'},

        {'methods': 'GET, POST', 'link': '/whitelist/user', 'desc': 'data for all whitelisted users'},
        {'methods': 'GET, DELETE', 'link': '/whitelist/user/username', 'desc': 'data for a single whitelisted user'},

        {'methods': 'GET, POST', 'link': '/whitelist/usersubreddit', 'desc': 'data for all whitelisted user/subreddit pairs'},
        {'methods': 'GET, PUT, DELETE', 'link': '/whitelist/usersubreddit/name', 'desc': 'data for a single whitelisted user/subreddit pair'},
    ]

    methods = []
    links = []
    descs = []

    for e in endpoints:
        methods.append(e['methods'])
        links.append(e['link'])
        descs.append(e['desc'])

    return render_template('index.html', count=len(endpoints), methods=methods, links=links, descs=descs)


@app.route('/users', methods=['GET', 'POST'])
def users():
    if request.method == 'GET':
        return jsonify(get_all_data())

    elif request.method == 'POST':
        if check_password(request.form['password']):
            if not user_exists(request.form['username']):
                cur = mysql.connection.cursor()
                now_timestamp = timestamp()
                data = execute_insert('users', ['username', 'subreddit', 'type', 'content', 'date'],
                                      (request.form['username'], request.form["subreddit"], request.form["type"], request.form["content"].encode('unicode_escape'), now_timestamp))
                return jsonify(data)

            else:
                return make_error("User already exists")
        else:
            return make_error("Invalid password")

    else:
        return make_error("Invalid request method")


@app.route('/users/<username>', methods=['GET', 'PUT', 'DELETE'])
def user(username):
    if request.method == 'GET':
        if user_exists(username):
            data = execute_select("""SELECT * FROM users WHERE username = %s""", (username,))

            return_data = {'status': 'success', 'data': data}
            return jsonify(return_data)
        else:
            return make_error("User does not exist")

    elif request.method == 'PUT':
        if check_password(request.form['password']):
            if request.form['username'] != '' and request.form['subreddit'] != '' and request.form['type'] != '' and request.form['content'] != '':
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
                            'data': {'username': request.form['username'], 'subreddit': request.form["subreddit"], 'type': request.form["type"], 'content': request.form["content"],
                                     'date': now_timestamp}
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
        else:
            return make_error("Invalid password")

    elif request.method == 'DELETE':
        if check_password(request.form['password']):
            if user_exists(username):
                data = execute_delete('users', 'username', username)
                return jsonify(data)

            else:
                return make_error("User does not exist")
        else:
            return make_error("Invalid password")

    else:
        return make_error("Invalid request method")


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


@app.route('/whitelist/subreddit', methods=['GET', 'POST'])
def subreddit_whitelist_all():
    if request.method == 'GET':
        data = execute_select("SELECT * FROM subreddit_whitelist")
        subreddit_list = []
        for s in data:
            subreddit_list.append(s['subreddit'])

        return_data = {'status': 'success', 'data': subreddit_list}
        return return_data

    elif request.method == 'POST':
        if check_password(request.form['password']):
            if not subreddit_whitelist_exists(request.form['subreddit']):
                data = execute_insert('subreddit_whitelist', ['subreddit'], (request.form['subreddit'],))
                return jsonify(data)
            else:
                return make_error("Subreddit already whitelisted")
        else:
            return make_error("Invalid password")

    else:
        return make_error("Invalid request method")


@app.route('/whitelist/subreddit/<subreddit>', methods=['GET', 'DELETE'])
def subreddit_whitelist(subreddit):
    if request.method == 'GET':
        if subreddit_whitelist_exists(subreddit):

            return_data = {'status': 'success', 'data': {'whitelisted': True}}
            return jsonify(return_data)
        else:
            return make_error("Subreddit not in whitelist")
    elif request.method == 'DELETE':
        if check_password(request.form['password']):
            if subreddit_whitelist_exists(subreddit):
                data = execute_delete('subreddit_whitelist', 'subreddit', subreddit)
                return jsonify(data)
            else:
                return make_error("Subreddit not in whitelist")
        else:
            return make_error("Invalid password")

    else:
        return make_error("Invalid request method")


@app.route('/whitelist/user', methods=['GET', 'POST'])
def user_whitelist_all():
    if request.method == 'GET':
        data = execute_select("SELECT * FROM user_whitelist")
        user_list = []
        for u in data:
            user_list.append(u['username'])

        return_data = {'status': 'success', 'data': user_list}
        return jsonify(return_data)

    elif request.method == 'POST':
        if check_password(request.form['password']):
            if not user_whitelist_exists(request.form['username']):
                data = execute_insert('user_whitelist', ['username'], (request.form['username'],))
                return jsonify(data)
            else:
                return make_error("User already whitelisted")
        else:
            return make_error("Invalid password")

    else:
        return make_error("Invalid request method")


@app.route('/whitelist/user/<username>', methods=['GET', 'DELETE'])
def user_whitelist(username):
    if request.method == 'GET':
        if user_whitelist_exists(username):

            return_data = {'status': 'success', 'data': {'whitelisted': True}}
            return jsonify(return_data)
        else:
            return make_error("User not in whitelist")
    elif request.method == 'DELETE':
        if check_password(request.form['password']):
            if user_whitelist_exists(username):
                data = execute_delete('user_whitelist', 'username', username)
                return jsonify(data)
            else:
                return make_error("User not in whitelist")
        else:
            return make_error("Invalid password")

    else:
        return make_error("Invalid request method")


@app.route('/whitelist/usersubreddit', methods=['GET', 'POST'])
def user_subreddit_whitelist_all():
    if request.method == 'GET':
        data = execute_select("SELECT * FROM user_subreddit_whitelist")

        fixed_data = {}
        for u in data:
            fixed_data[u['username']] = u['subreddits']

        return_data = {'status': 'success', 'data': fixed_data}
        return return_data

    elif request.method == 'POST':
        if check_password(request.form['password']):
            if not user_subreddit_whitelist_exists(request.form['username']):
                data = execute_insert('user_subreddit_whitelist', ['username', 'subreddits'], (request.form['username'], request.form['subreddits']))
                return jsonify(data)
            else:
                return make_error("User Subreddit whitelist already exists")
        else:
            return make_error("Invalid password")

    else:
        return make_error("Invalid request method")


@app.route('/whitelist/usersubreddit/<username>', methods=['GET', 'PUT', 'DELETE'])
def user_subreddit_whitelist(username):
    if request.method == 'GET':
        if user_subreddit_whitelist_exists(username):
            data = execute_select("""SELECT * FROM user_subreddit_whitelist WHERE username = %s""", (username,))

            fixed_data = {data['username']: data['subreddits']}
            return_data = {'status': 'success', 'data': fixed_data}
            return return_data
        else:
            return make_error("User Subreddit whitelist does not exist")
    elif request.method == 'PUT':
        if check_password(request.form['password']):
            if request.form['subreddits'] != '':
                if user_subreddit_whitelist_exists(username):
                    cur = mysql.connection.cursor()

                    return_message = {}
                    try:
                        cur.execute("""UPDATE user_subreddit_whitelist SET subreddits = %s WHERE username = %s""", (request.form['subreddits'], username))
                        mysql.connection.commit()

                        return_message = jsonify({
                            'status': 'success', 'action': 'UPDATE',
                            'data': {'username': username, 'subreddits': request.form['subreddits']}
                        })
                    except Exception as e:
                        return_message = jsonify({'status': 'error', 'action': 'UPDATE', 'exception': str(type(e).__name__), 'message': 'Error during execution of query'})
                    finally:
                        cur.close()
                        return return_message

                else:
                    return make_error("User does not exist")
        else:
            return make_error("Invalid password")

    elif request.method == 'DELETE':
        if check_password(request.form['password']):
            if user_subreddit_whitelist_exists(username):
                data = execute_delete('user_subreddit_whitelist', 'username', username)
                return jsonify(data)
            else:
                return make_error("User Subreddit whitelist does not exist")
        else:
            return make_error("Invalid password")

    else:
        return make_error("Invalid request method")


if __name__ == '__main__':
    app.run(host='127.0.0.1', port=8080, debug=False)
