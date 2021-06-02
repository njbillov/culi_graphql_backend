#!venv/bin/python
from flask import Flask, jsonify, g, request, Response, render_template
import graphene
from database import db_connection
from graphene_file_upload.flask import FileUploadGraphQLView
import query
import json
import os
import utils
import sys
import time
from recipe_parser import RecipeParser
from recipe_loader import clear_one_recipe, update_recipe
import logging

app = Flask(__name__)
handler = logging.FileHandler("debug.log")
app.logger.addHandler(handler)
app.logger.setLevel(logging.DEBUG)


@app.route('/recipes')
def recipe_search():
    rp = RecipeParser()
    recipe_names = rp.get_recipe_names()
    return render_template("recipe_search.html", recipes=recipe_names)


@app.route('/recipes/<recipe_id>')
def display_recipes(recipe_id: str):
    print("Displaying recipe")
    rp = RecipeParser()
    recipe_json, recipe_html, _ = rp.get_recipe(recipe_id=recipe_id)
    return render_template("recipe_display.html", rendering=recipe_html, recipe=recipe_json)

@app.route('/recipes/<recipe_id>/update')
def update_recipe_data(recipe_id):
    rp = RecipeParser()
    recipe_json, _, filename = rp.get_recipe(recipe_id=recipe_id)

    with open(filename, 'w') as file:
        print(f"Writing newest version of {recipe_json['recipe_name']} locally")
        json.dump(recipe_json, file, indent=2, sort_keys=True)
    
    update_recipe(recipe_json, is_dict=True)
    return {"response": "Updating the recipe"}

@app.route('/recipes/<recipe_id>/delete')
def delete_recipe(recipe_id):
    clear_one_recipe(int(recipe_id))
    return {"response": "Deleting the recipe"}

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'neo4j_db'):
        g.neo4j_db.close()

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
        schema=query.schema,
        graphiql=True
    )
)

if __name__ == '__main__':
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = 8080

    app.run(host='0.0.0.0', port=port)
