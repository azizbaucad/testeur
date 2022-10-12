from flask import Flask, request, jsonify, Config
from script.function import *
from script.function_post import *
import yact
import requests
import flask
from flask_cors import CORS
import pandas as pd

import jsonpickle

app = Flask(__name__)
CORS(app)


class YactConfig(Config):
    def from_yaml(self, config_file, directory=None):
        config = yact.from_file(config_file, directory=directory)
        for section in config.sections:
            self[section.upper()] = config[section]


def cfg():
    with open(os.path.dirname(os.path.abspath(__file__)) + './script/config.yaml', "r") as ymlfile:
        cfg = yaml.load(ymlfile.read(), Loader=yaml.FullLoader)
        return cfg


#  Les fonctions utiles
def add_headers(response):
    response.headers.add('Content-Type', 'application/json')
    response.headers.add('X-Frame-Options', 'SAMEORIGIN')
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Methods', 'PUT, GET, POST, DELETE, OPTIONS')

    return response


# La fonction adminToken
def adminToken():
    data = {
        'grant_type': 'client_credentials',
        'client_id': CLIENT_ID,
        'client_secret': CLIENT_SECRET
    }

    url = URI

    response = requests.post(url, data=data)

    if response.status_code > 200:
        return {"message": "Username ou Password Incorrect", 'status': 'error'}
    tokens_data = response.json()
    ret = {
        'tokens': {"access_token": tokens_data['access_token'],
                   "token_type": tokens_data['token_type'],
                   },
        "status": 'success',
    }
    return ret


# la fonction error

def error(message):
    return jsonify({
        'success': False,
        'message': message
    })


# simple inventaire info
@app.route('/simpleinventaire')
def simpleinventaire():
    # data = []
    con = None
    try:
        con = connect()
        cur = con.cursor()
        cur.execute("SElect * from historique_diagnostic limit 4 ;")
        data = cur.fetchall()
        cur.close()
        con.commit()
        # return jsonpickle.encode(data)
    except(Exception, psycopg2.DatabaseError) as error:
        print(error)
    finally:
        if con is not None:
            con.close()
    return data


# requete historique/date
@app.route('/historique', methods=['POST'])
def historique():
    return get_historique_by_date()


# return historique
@app.route('/get_historique', methods=['GET', 'POST'])
def get_historique_():
    con = connect()
    if request.method == 'GET':
        res = get_historique()
    if request.method == 'POST':
        data = request.get_json()
        date = data['date']
        if date is not None and date != "":
            # Mettre ici la requete
            query = "Select numero, date_, created_at from historique_diagnostic where anomalie like '%Coupure%' and (NOW()::date  -  date_) >= 30 ;"
            data_ = pd.read_sql(query, con)
            print(data_)

            res = get_historique()
        else:
            return "ERROR 404", 404
    return


@app.route('/get_test_historique', methods=['GET', 'POST'])
def get_test_historique():
    con = connect()
    if request.method == 'GET':
        res = get_historique()
    if request.method == 'POST':
        data = request.get_json()
        dateFrom = data['dateFrom']
        dateTo = data['dateTo']
        if dateFrom is not None and dateFrom != "" and dateTo is not None and dateTo != "":
            print(dateFrom)
            print(dateTo)
        query = "Select numero, date_, created_at from historique_diagnostic where anomalie like '%Coupure%' and is_anomalie = 'true' and date_ BETWEEN '{}'  AND  '{}'".format(dateFrom, dateTo)
        data_ = pd.read_sql(query, con)
        print(data_)
        res = data_.to_dict(orient='records')
        return res
    return res

# la fonction create_users
@app.route('/users/', methods=['POST'])
def create_user():
    try:
        print()
        headers = flask.request.headers
        # data_token = decodeToken(token)
        taille = 0
        if request.headers.get('Authorization').startswith('Bearer') and len(headers.get('Authorization').split()) == 2:
            token = headers.get('Authorization').split()[1]

        else:
            return {"message": "invalid token", 'code': HTTPStatus.UNAUTHORIZED}
            print(token)
        print(token)
        data_token = decodeToken(token)
        code = data_token['code']
        name = data_token['data']['name']
        if code == 200:
            if getRoleToken(token) == 'admin':
                url = URI_USER

                body = request.json
                for field in ['firstName', 'lastName', 'username', 'password']:
                    if field not in body:
                        return error(f"Field {field} is missing"), 400
                data = {
                    "firstName": body['firstName'],
                    "lastName": body['lastName'],
                    "enabled": "true",
                    "username": body['username'],
                    "credentials": [
                        {
                            "type": "password",
                            "value": body['password'],
                            "temporary": False

                        }
                    ]
                }
                # return data
                donnee = adminToken()
                headers = get_keycloak_headers()
                response = requests.post(url, headers=headers, json=data)
                if response.status_code == 400:
                    return {"message": "Le nom de l'utilisateur existe deja", 'status': 'error',
                            'code': response.status_code}
                if response.status_code > 201:
                    return {"message": "Erreur", 'status': 'error', 'code': response.status_code}
                response = jsonify(
                    {'status': 'Success', 'data': 'Utilisateur Cree avec success', 'code': HTTPStatus.OK})
                # Mettre ici les logs
                return add_headers(response)
            return {"message": "invalid user", 'code': HTTPStatus.UNAUTHORIZED}
        else:
            token = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJJejVmc21zTU9KRDh1UHFxcWN6SFQ0NkhnSkUxTUZleV9KV1BuQ1BNMWxBIn0.eyJleHAiOjE2NjU0MTY5MzUsImlhdCI6MTY2NTQxNjYzNSwianRpIjoiZTAwMzYxNTUtOWMzOS00MzRiLWE3YjAtNWI2YzNhMmIzY2VhIiwiaXNzIjoiaHR0cDovL2xvY2FsaG9zdDo4MDgwL2F1dGgvcmVhbG1zL25ldHdvcmsiLCJhdWQiOlsicmVhbG0tbWFuYWdlbWVudCIsImFjY291bnQiXSwic3ViIjoiZGI0NWViMWYtY2QyNi00YmE4LTkyNDctYTVmYzhiOGUyMTZkIiwidHlwIjoiQmVhcmVyIiwiYXpwIjoicmVzdC1jbGllbnQiLCJzZXNzaW9uX3N0YXRlIjoiZDc1ODRjMGMtNmU4NS00MTA2LTg3NWEtMTlmNmI1NTU1ZjJlIiwiYWNyIjoiMSIsInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJvZmZsaW5lX2FjY2VzcyIsInVtYV9hdXRob3JpemF0aW9uIl19LCJyZXNvdXJjZV9hY2Nlc3MiOnsicmVhbG0tbWFuYWdlbWVudCI6eyJyb2xlcyI6WyJ2aWV3LXJlYWxtIiwidmlldy1pZGVudGl0eS1wcm92aWRlcnMiLCJtYW5hZ2UtaWRlbnRpdHktcHJvdmlkZXJzIiwiaW1wZXJzb25hdGlvbiIsInJlYWxtLWFkbWluIiwiY3JlYXRlLWNsaWVudCIsIm1hbmFnZS11c2VycyIsInF1ZXJ5LXJlYWxtcyIsInZpZXctYXV0aG9yaXphdGlvbiIsInF1ZXJ5LWNsaWVudHMiLCJxdWVyeS11c2VycyIsIm1hbmFnZS1ldmVudHMiLCJtYW5hZ2UtcmVhbG0iLCJ2aWV3LWV2ZW50cyIsInZpZXctdXNlcnMiLCJ2aWV3LWNsaWVudHMiLCJtYW5hZ2UtYXV0aG9yaXphdGlvbiIsIm1hbmFnZS1jbGllbnRzIiwicXVlcnktZ3JvdXBzIl19LCJhY2NvdW50Ijp7InJvbGVzIjpbIm1hbmFnZS1hY2NvdW50IiwibWFuYWdlLWFjY291bnQtbGlua3MiLCJ2aWV3LXByb2ZpbGUiXX19LCJzY29wZSI6ImVtYWlsIHByb2ZpbGUiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsInByZWZlcnJlZF91c2VybmFtZSI6ImF6aXoifQ.KFWuNXW8ztx8FcJg0WzOuc29j1rSinFvkLOjoRxAKLh4jUl8z40kdwwLCSvuH70eI6wMYkVnP9CLDdhCvlRN7MkjA2eIGTNG4hWX1uP6MtS0LsBRtLqGIk1e1vDixBNJo4XrfUcTQXWPc_liMReeOez9S1Fho_CwYPbNk57Ann8FP5lzkZ67jc2EdWOF9abC1hoRDFOLK-9ZZby_WzhmMA0PKlTNdhJyo_0ZW9g2wKiS_Rps5qiMpmU-gbXfsNNOuRE27UTBYj4jmux6SQw5X3y5-77WGvxTcYMI_rjRdy6UqDikvZDB9bh360mazTC1EDHh7-GfigqxjTmPaDhGqA"
            return decodeToken(token)

        # code = decodeToken(token)['code']

    except ValueError:
        return jsonify({'status': 'Error', 'error': ValueError})


# creation de la fonction get_keycloak_headers
def get_keycloak_headers():
    donnee = adminToken()
    token_admin = donnee['tokens']['access_token']
    return {
        'Authorization': 'Bearer' + token_admin,
        'Content-type': 'application/json'
    }


@app.route('/')
def hello_world():  # put application's code here
    return 'Hello World! WELCOME TO Saytu Network Backend'


@app.route('/auth', methods=['POST'])
def get_token():
    # TODO : Control username et password
    body = request.get_json(force=True)

    data = {

        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": 'password',
        'username': body['username'],
        'password': body['password']
    }

    url = URI
    response = requests.post(url, data=data)
    if response.status_code > 200:
        messageLogging = body['username'] + "a tente de se connecter"
        return {"message": "Username ou Password Incorrect", 'code': HTTPStatus.BAD_REQUEST}

    tokens_data = response.json()

    ret = {
        'tokens': {
            "access_token": tokens_data['access_token'],
            "refresh_token": tokens_data['refresh_token'],
        }
    }
    messageLogging = body['username'] + "s'est connecté avec success"

    return jsonify({"message": "ok", "codes": 200}, ret), 200


# La fonction get_user_by_id
def get_user_by_id(userId):
    try:
        url = URI_USER + '/' + userId
        donnee = adminToken()
        token_admin = donnee['tokens']['access_token']
        response = requests.get(url,
                                headers={'Authorization': 'Bearer {}'.format(token_admin)})
        if response.status_code > 200:
            return {"message": "Erreur", 'status': 'error', 'code': response.status_code}
        tokens_data = response.json()
        data = {
            "enabled": tokens_data['enabled'],
            "id": tokens_data['id'],
            "firstName": tokens_data['firstName'],
            "lastName": tokens_data['lastName'],
            "username": tokens_data['username'],
        }
        response = {'status': 'Success', 'data': data, 'code': HTTPStatus.OK}
        return response
    except ValueError:
        return jsonify({'status': 'Error', 'error': ValueError})


# la fonction get_info_user
def get_info_user(userId):
    try:
        url = URI_USER + '/' + userId + '/role-mappings/realm'
        donnee = adminToken()
        token_admin = donnee['tokens']["access_token"]
        response = requests.get(url,
                                headers={'Authorization': 'Bearer {}'.format(token_admin)})
        if response.status_code > 200:
            return {"message": "Erreur", 'status': 'error', 'code': response.status_code}
            tokens_data = response.json
            data = {
                "name": tokens_data[0]['name'],
                "id": tokens_data[0]['id']
            }
            return data
    except ValueError:
        return jsonify({'status': 'Error', 'error': ValueError})


# api de recupération des users

@app.route('/users/', methods=['GET'])
def all_users():
    print(decodeToken(request.headers.get('Authorization').split()[1]))
    # ffdecodeToken()
    try:
        headers = flask.request.headers
        # print
        if request.headers.get('Authorization'):
            if request.headers.get('Authorization').startswith('Bearer'):
                bearer = headers.get('Authorization')
                taille = len(bearer.split())
                if taille == 2:
                    token = bearer.split()[1]
                else:
                    return {"message": "invalid token roel", 'code': HTTPStatus.UNAUTHORIZED}
            else:
                return {"message": "invalid token orl", 'code': HTTPStatus.UNAUTHORIZED}
        else:
            return {"message": "invalid token rlo", 'code': HTTPStatus.UNAUTHORIZED}

        data = decodeToken(token)
        code = data['code']
        # name = data['data']['name']
        if code == 200:
            if getRoleToken(token) == 'admin' or getRoleToken(token) == 'sf':

                url = URI_USER + '?max=1000'
                donnee = adminToken()
                token_admin = donnee['tokens']["access_token"]
                response = requests.get(url,
                                        headers={'Authorization': 'Bearer {}'.format(token_admin)})
                if response.status_code > 200:
                    return {"message": "Erreur", 'status': 'error', 'code': response.status_code}
                tokens_data = response.json()
                # return tokens_data[0]
                result = []
                for i in range(len(tokens_data)):
                    data = {
                        "enabled": tokens_data[i]['enabled'],
                        "id": tokens_data[i]['id'],
                        "firstName": tokens_data[i]['firstName'].split(' ', 1)[0],
                        "lastName": tokens_data[i]['lastName'].upper(),
                        "username": tokens_data[i]['username'],
                        "profil": get_info_user(tokens_data[i]['id']),
                    }
                    result.append(data)
                # return result
                response = jsonify({'status': 'Success', 'data': result, 'code': HTTPStatus.OK})
                # messageLogging = name + " a consulté la liste des utilisateurs "
                # message_log = {
                #     "url.path": request.base_url,
                #     "http.request.method": request.method,
                #     "client.ip": getIpAdress(),
                #     "event.message": messageLogging,
                #     "process.id": os.getpid(),
                # }
                # log_app(message_log)
                # logger_user(messageLogging, LOG_AUTHENTIFICATION)
                return add_headers(response)
            # messageLogging = name + " a tenté de consulter la liste des utilisateurs "
            # message_log = {
            #     "url.path": request.base_url,
            #     "http.request.method": request.method,
            #     "client.ip": getIpAdress(),
            #     "event.message": messageLogging,
            #     "process.id": os.getpid(),
            # }
            # log_app(message_log)
            # logger_user(messageLogging, LOG_AUTHENTIFICATION)
            return {"message": "invalid user", 'code': HTTPStatus.UNAUTHORIZED}
        else:
            return decodeToken(token)
    except ValueError:
        return jsonify({'status': 'Error ', 'error': ValueError})


# Recuperation des variables
CLIENT_ID = cfg()['CLIENT_ID']
CLIENT_SECRET = cfg()['CLIENT_SECRET']
GRANT_TYPE = cfg()['GRANT_TYPE']
# HOST = cfg()['CLIENT_ID']
# PORT = sysEnvOrDefault("PORT", app.config['PORT'])
URI = cfg()['URI']
URI_USER = cfg()['URI_USER']
URI_ROLES = cfg()['URI_ROLES']
REALM = cfg()['REALM']
URI_BASE = cfg()['URI_BASE']

print(
    "CLIENT_ID" + CLIENT_ID + "CLIENT_SECRET" + CLIENT_SECRET + "GRANT_TYPE" + GRANT_TYPE + "URI" + URI + "URI_USER" + URI_USER + "URI_ROLES" + URI_ROLES + "REALM" + REALM + "URI_BASE" + URI_BASE)
field = "aziz"
print(f"error() : Field {field} is missing", 400)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
