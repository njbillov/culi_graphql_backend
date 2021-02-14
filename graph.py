#!venv/bin/python
from flask import Flask, jsonify, g, request, Response
from graphene_file_upload.flask import FileUploadGraphQLView
from query import schema
from neo4j import GraphDatabase,  basic_auth
import os
import utils
import time

app = Flask(__name__)

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'neo4j_db'):
        g.neo4j_db.close()

@app.route('/')
def hello_world():
    return "Hello World"

# @app.before_request
# def log_request_info():
#     print('Headers: %s', request.headers)
#     print('Body: %s', request.query_string)

@app.before_request
def store_time():
    g.start = time.time()

@app.teardown_request
def log_time(exception=None):
    print(f'Request took {time.time() - g.start} seconds to serve')

app.add_url_rule(
    '/graphql',
    methods=['GET', 'POST'],
    view_func=FileUploadGraphQLView.as_view(
        'graphql',
        schema=schema,
        graphiql=True
    )
)

if __name__ == '__main__':
    # print(utils.upload_object())
    # utils.test_get_object()
    app.run(host='0.0.0.0', port=8080)
