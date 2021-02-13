#!venv/bin/python
import json
import os
import shutil
import sys

from neo4j import GraphDatabase, basic_auth

if not os.path.exists('.dev'):
    if os.path.exists('.db_uri'):
        with open('.db_uri', 'r') as file:
            os.environ['DB_URI'] = file.read().strip()
    if os.path.exists('.db_password'):
        with open('.db_password', 'r') as file:
            os.environ['DB_PASSWORD'] = file.read().strip()

url = os.getenv('DB_URI') if os.getenv('DB_URI') is not None else "bolt://localhost"
password = os.getenv('DB_PASSWORD') if os.getenv('DB_PASSWORD') is not None else 'memphis-place-optimal-velvet-phantom-127'

driver = GraphDatabase.driver(url, auth=basic_auth("neo4j", password), encrypted=False)

neo4j_db = driver.session()


def clear_recipes():
    query = '''
    MATCH (r:Recipe) WHERE toInteger(r.recipeId) < 1000 DETACH DELETE r RETURN r;
    '''
    results = neo4j_db.run(query)


def clear_one_recipe(recipe_id: int) -> bool:
    parameters = {'recipeId': recipe_id}
    query = '''
    MATCH (r:Recipe {recipeId: $recipeId}) DETACH DELETE r RETURN r
    '''
    results = neo4j_db.run(query, parameters=parameters)
    count: int = 0
    deleted: bool = False
    for record in results:
        deleted |= True
        count += 1
    print(f"Delete {count} recipe duplicate(s) from the database")
    return deleted


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
    if len(sys.argv) != 3:
        print('Usage: ./recipe_loader clear|add recipe_directory')
        return
    command = sys.argv[1]
    directory = sys.argv[2]
    if command.lower() == 'clear':
        print(f'Deleting recipe(s): {directory}')
        if os.path.isfile(directory):
            with open(directory, 'r') as file:
                json_string = file.read()
                d = json.loads(json_string)
                recipe_id = int(d["recipe_id"])
                print(f'Deleting {d["recipe_name"]} (recipeId: {recipe_id})')
                clear_one_recipe(recipe_id)
            return
        else:
            abs_directory: str = os.path.abspath(directory)
            _, _, filenames = next(os.walk(abs_directory))
            # clear_recipes()
            print('Deleting all recipes in directory')
            for filename in filenames:
                with open(directory, 'r') as file:
                    json_string = file.read()
                    d = json.loads(json_string)
                    recipe_id = d["recipeId"]
                    print(f'Deleting {d["recipeName"]} (recipeId: {recipe_id}')
                    clear_one_recipe(recipe_id)


    elif command.lower() == 'add':
        # print(f'Adding recipe(s): {directory}')
        if os.path.isfile(directory):
            print(f'Adding {"".join(os.path.splitext(directory)[-2:])}')
            with open(directory, 'r') as file:
                json_string = file.read()
                load_recipe(json_string)
            return
        else:
            abs_directory: str = os.path.abspath(directory)
            _, _, filenames = next(os.walk(abs_directory))
            # clear_recipes()
            print(f'Adding all recipes in {directory}')
            for filename in filenames:
                with open(os.path.join(directory, filename), 'r') as file:
                    json_string = file.read()
                    load_recipe(json_string)

    else:
        print('Usage: ./recipe_loader clear|add recipe_directory')
        return


if __name__ == '__main__':
    main()
