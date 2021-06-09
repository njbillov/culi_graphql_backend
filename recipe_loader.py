#!venv/bin/python
import json
import os
import re
import shutil
import sys
# from textblob import TextBlob, Word, tokenizers

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

def get_session():
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
    return neo4j_db


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
    with get_session() as session:
        results = session.run(query, parameters=parameters)
        count: int = 0
        deleted: bool = False
        for record in results:
            deleted |= True
            count += 1
        print(f"Delete {count} recipe duplicate(s) from the database")
        return deleted


def load_recipe(json_string: str, is_dict=False):
    if not is_dict :
        j = json.loads(json_string)
    else:
        j = json_string
    recipe_id = j['recipe_id']
    recipe_name = j['recipe_name']
    tags = j['tags']
    new_tags = {}
    for k, v in tags.items():
        new_tags[f'tag_{k}'] = v
    tags = new_tags
    skills = set()
    for macro_step in j['steps']:
        for micro_step in macro_step['steps']:
            for skill in micro_step['skills']:
                skills.add(skill['name'].lower())
    skills = list(skills)
    params = dict()
    params["recipe_id"] = int(recipe_id)
    params["recipe_name"] = recipe_name
    if is_dict:
        params["json"] = json.dumps(j)
    else:
        params["json"] = json_string
    params["skills"] = skills
    params.update(tags)
    tag_string = ', '.join([f'{key}: ${key}' for key, _ in tags.items()])
    query = "CREATE (r:Recipe {recipeId: $recipe_id, recipeName: $recipe_name, skills: $skills, json: $json, " + tag_string + "}) RETURN r;"
    with get_session() as session:
        results = session.run(query, parameters=params)

        session.close()

    with get_session() as session:
        create_skills_query = '''UNWIND $skills AS skill
        MERGE (s:Skill {name: skill})
        RETURN s
        '''
        print(f'Skills parameter: {skills}')
        results = session.run(create_skills_query, parameters={'skills': skills})
        print(results.data())
        session.close()

def merge_recipe(recipe_id):
    params = {'recipe_id': recipe_id}
    query = '''MATCH (r:Recipe {recipeId: $recipe_id}) 
        WITH collect(r) AS nodes, count(r) as before_count
        CALL apoc.refactor.mergeNodes(nodes)
        YIELD r
        RETURN before_count, count(r) as after_count
    '''

    with get_session() as session:
        results = session.run(query, parameters=params)

        record = results.single()
        before_count = record.get("before_count")
        after_count = record.get("after_count")

        print(f'When updating recipe {recipe_id} before merge instances: {before_count} and now {after_count}')

    return


def update_recipe(json_string, is_dict=True):
    if not is_dict:
        j = json.loads(json_string)
    else:
        j = json_string
        json_string = json.dumps(json_string)

    params = {'recipe_id': int(j["recipe_id"])}
    equality_query = "MATCH (r:Recipe {recipeId: $recipe_id}) return r as previous_r, r.json as recipe_json"

    recipe_json = None
    previous_r = None
    existing_versions = 0
    with get_session() as session:
        results = session.run(equality_query, parameters=params)

        for record in results:
            recipe_json = record.get("recipe_json")
            previous_r = record.get("previous_r")
            existing_versions += 1

    if existing_versions > 1:
        merge_recipe(params['recipe_id'])

    if json_string == recipe_json:
        print(f"{j['recipe_name']} in database is already up-to-date")
        return
    elif previous_r is None:
        print(f"{j['recipe_name']} not in the database yet, adding it in now")
        load_recipe(json_string, is_dict=is_dict)
        return
    recipe_id = j['recipe_id']
    recipe_name = j['recipe_name']
    tags = j['tags']
    new_tags = {}
    for k, v in tags.items():
        new_tags[f'tag_{k}'] = v
    tags = new_tags
    tag_string = ', '.join([f'{key}: ${key}' for key, _ in tags.items()])
    skills = set()
    for macro_step in j['steps']:
        for micro_step in macro_step['steps']:
            for skill in micro_step['skills']:
                skills.add(skill['name'].lower())
    skills = list(skills)
    params = {"recipe_id": int(recipe_id), "recipe_name": recipe_name, "json": json_string, "skills": skills, **tags}
    query = '''MATCH (r:Recipe {recipeId: $recipe_id})
                SET r = {recipeId: $recipe_id, recipeName: $recipe_name, skills: $skills, json: $json,
            '''\
            + tag_string +\
            '''
            }
                RETURN r.recipeId as recipeId
            '''
    with get_session() as session:
        results = session.run(query, parameters=params)

        r = None
        for record in results:
            r = record.get('recipeId')
            print(f'Updating recipe {r}')

        create_skills_query = '''UNWIND $skills AS skill
        MERGE (s:Skill {name: skill})
        RETURN s
        '''

    with get_session() as session:
        results = session.run(create_skills_query, parameters={'skills': skills})

        for record in results:
            _ = record.get("s")
        print(f'Updated the {params["recipe_name"]}')


# def check_unusual_characters(recipe_text):
#     error_locations = []
#     for key, text in recipe_text.items():
#         if re.search('[^a-zA-Z0-9-():;\.!\?\s,\'/"]', text):
#             print(f"There was likely an error in {key}")
#             error_locations.append(key)
#             print(text)

#     return len(error_locations) == 0


# def check_spelling(recipe_text):
#     error_locations = []
#     for key, text in recipe_text.items():
#         for i, word in enumerate(TextBlob(text).words):

#             checker_list = Word(word).spellcheck()
#             words_list = [pair[0] for pair in checker_list]
#             word_prob = checker_list[words_list.index(word)][1] if word in words_list else -1
#             if word_prob != -1 or "'" in word:
#                 continue
#             else:
#                 error_locations.append(f'{key}: Confidence in {word} at index {i} too low, could be {checker_list[:3]}')
#                 print(error_locations[-1])

#     return len(error_locations) == 0, error_locations


def check_recipe(recipe_json):
    j = json.loads(recipe_json)
    valid = True

    recipe_text = {}
    for i, macro_step in enumerate(j['steps']):
        for k, micro_step in enumerate(macro_step['steps']):
            recipe_text[f'step {i + 1}.{k + 1}'] =  micro_step['text']

    recipe_text['description'] = j['description']
    recipe_name = j['recipe_name']

    # if not check_unusual_characters(recipe_text):
    #     print(f"{recipe_name} seemed to have unusual characters in it")
    #     valid = False

    # ok, spelling_errors = check_spelling(recipe_text)
    # if not ok:
    #     print(f"{recipe_name} seems to have spelling errors in it")
    #     valid = False

    if valid:
        print(f"{recipe_name} is ready to add to the database")
    else:
        print(f"{recipe_name} is not ready to add to the database")


def purge_skills(files):
    skills = set()

    for file in files:
        with open(file, 'r') as f:
            recipe_dict = json.loads(f.read())
            for macro_step in recipe_dict['steps']:
                for micro_step in macro_step['steps']:
                    for skill in micro_step['skills']:
                        skills.add(skill['name'].lower())

    get_current_skills_query = '''MATCH (s:Skill) RETURN s.name AS skill'''

    with get_session() as session:
        results = session.run(get_current_skills_query)
        db_skills = set()
        for record in results:
            db_skills.add(record.get('skill').lower())

        print(f'Skills in the database: {", ".join(db_skills)}')

        new_skills = list(skills - db_skills)
        stale_skills = list(db_skills - skills)

        print(f'Skills in database but not in recipes: {", ".join(stale_skills)}')
        print(f'Skills in recipe directory but not in database: {", ".join(new_skills)}')

        if len(stale_skills) > 0:
            print("Purging the stale skills from the database")
            remove_skills_query = '''UNWIND $stale_skills AS skill
            OPTIONAL MATCH (s:Skill {name: skill})
            DETACH DELETE s
            RETURN count(s) as count
            '''

            session.run(remove_skills_query, parameters={'stale_skills': stale_skills})

            deleted_skills = 0
            for record in results:
                deleted_skills = record.get('count')
            print(f'{deleted_skills} skills successfully removed from the database')


def main():
    if len(sys.argv) != 3:
        print('Usage: ./recipe_loader clear|update|add|check recipe_directory')
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

    elif command.lower() == 'update':
        if os.path.isfile(directory):
            print(f'Updating {"".join(os.path.splitext(directory)[-2:])}')
            with open(directory, 'r') as file:
                json_string = file.read()
                update_recipe(json_string, is_dict=False)
            return

        else:
            abs_directory = os.path.abspath(directory)
            _, _, filenames = next(os.walk(abs_directory))

            print(f'Updating all recipes in {directory}')
            for filename in filenames:
                with open(os.path.join(directory, filename), 'r') as file:
                    json_string = file.read()
                    update_recipe(json_string, is_dict=False)
    elif command.lower() == 'check':
        if os.path.isfile(directory):
            print(f'Checking {"".join(os.path.splitext(directory)[-2:])}')
            with open(directory, 'r') as file:
                json_string = file.read()
                check_recipe(json_string)
            return

        else:
            abs_directory = os.path.abspath(directory)
            _, _, filenames = next(os.walk(abs_directory))

            print(f'Checking all recipes in {directory}')
            for filename in filenames:
                with open(os.path.join(directory, filename), 'r') as file:
                    json_string = file.read()
                    check_recipe(json_string)
    elif command.lower() == 'purge_skills':
        if os.path.isfile(directory):
            print("Expecting a directory of recipes to purge skills.")

        abs_directory = os.path.abspath(directory)
        _, _, filenames = next(os.walk(directory))
        print('Fetching skills from all existing recipes')
        filenames = [os.path.join(directory, file) for file in filenames]

        purge_skills(filenames)

    else:
        print('Usage: ./recipe_loader clear|update|add|check recipe_directory')
        return


if __name__ == '__main__':
    main()
