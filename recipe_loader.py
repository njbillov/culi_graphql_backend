#!venv/bin/python
import json
import os
import shutil
import sys

from neo4j import GraphDatabase, basic_auth

url = "bolt://localhost"
password = 'memphis-place-optimal-velvet-phantom-127'

driver = GraphDatabase.driver(url, auth=basic_auth("neo4j", password), encrypted=False)

neo4j_db = driver.session()


def clear_recipes():
    query = '''
    MATCH (r:Recipe) WHERE toInteger(r.recipeId) < 1000 DETACH DELETE r RETURN r;
    '''
    results = neo4j_db.run(query)


def load_recipe(json_string: str):
    j = json.loads(json_string)
    recipe_id = j['recipe_id']
    recipe_name = j['recipe_name']
    skills = set()
    for macro_step in j['steps']:
        for micro_step in macro_step['steps']:
            for skill in micro_step['skills']:
                skills.add(skill['name'].lower())
    skills = list(skills)
    params = dict()
    params["recipe_id"] = int(recipe_id)
    params["recipe_name"] = recipe_name
    params["json"] = json_string
    params["skills"] = skills
    query = "CREATE (r:Recipe {recipeId: $recipe_id, recipeName: $recipe_name, skills: $skills, json: $json}) RETURN r;"
    results = neo4j_db.run(query, parameters=params)

    create_skills_query = '''UNWIND $skills AS skill 
    MERGE (s:Skill {name: skill})
    RETURN s
    '''
    results = neo4j_db.run(create_skills_query, parameters={'skills': skills})


def main():
    directory = sys.argv[1]
    print(str(sys.argv))

    abs_directory: str = os.path.abspath(directory)
    _, _, filenames = next(os.walk(abs_directory))
    clear_recipes()
    for filename in filenames:
        with open(os.path.join(directory, filename), 'r') as file:
            json_string = file.read()
            load_recipe(json_string)


if __name__ == '__main__':
    main()
