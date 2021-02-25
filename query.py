#!/usr/bin/env python3
from datetime import time, datetime

import graphene
import neo4j
from graphene_file_upload.scalars import Upload
from flask import g
from neo4j import GraphDatabase, basic_auth
from app_change_log import AppChangeLog
import random
import uuid
import json
import os

from typing import Tuple
from werkzeug.datastructures import FileStorage

from config import BUCKET
from utils import create_password, compare_password, presign_object, save_file, upload_file, upload_object

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


def get_db():
    if not hasattr(g, 'neo4j_db'):
        g.neo4j_db = driver.session()
    return g.neo4j_db


class QuestionType(graphene.Enum):
    FREE_RESPONSE = 'FREE_RESPONSE'
    CHOOSE_MANY = 'CHOOSE_MANY'
    CHOOSE_ONE = 'CHOOSE_ONE'
    STAR = 'STAR'
    YES_NO = 'YES_NO'
    END = 'END'
    INVALID = 'INVALID'


class SurveyType(graphene.Enum):
    TREE = 'TREE'
    FLAT_TREE = 'FLAT_TREE'
    FLAT = 'FLAT'
    UNKNOWN = 'UNKNOWN'


class FollowUpType(graphene.Enum):
    INPLACE = 'INPLACE'
    REFERENCE = 'REFERENCE'


class SurveyQuestion(graphene.Interface):
    title = graphene.String(required=True)
    type = graphene.Field(QuestionType, required=True)
    answered = graphene.Int()

    @classmethod
    def resolve_type(cls, instance, info):
        # This hack is to accept both cascading json and actual graphene types
        q_type = QuestionType.get(instance['type']) if isinstance(instance, dict) else instance.type
        print(f'type received: {q_type}')
        if q_type == QuestionType.FREE_RESPONSE:
            return FreeResponse
        elif q_type == QuestionType.CHOOSE_MANY:
            return ChooseMany
        elif q_type == QuestionType.CHOOSE_ONE:
            return ChooseOne
        elif q_type == QuestionType.STAR:
            return Star
        elif q_type == QuestionType.YES_NO:
            return YesNo
        print("Received unexpected type")
        return End


class FollowUp(graphene.ObjectType):
    questions = graphene.List(SurveyQuestion)
    start = graphene.Int()
    length = graphene.Int()
    type = graphene.Field(FollowUpType, required=True)

    @staticmethod
    def resolve_type(parent, info):
        if 'start' in parent and 'length' in parent:
            return FollowUpType.REFERENCE
        return FollowUpType.INPLACE


class ChooseMany(graphene.ObjectType):
    class Meta:
        interfaces = (SurveyQuestion,)

    type = QuestionType(default_value=QuestionType.CHOOSE_MANY, required=True)
    options = graphene.List(graphene.String, required=True)
    choices = graphene.List(graphene.Int)
    followUps = graphene.List(FollowUp, default_value=[])

    @staticmethod
    def resolve_type(parent, info):
        return QuestionType.CHOOSE_MANY


class ChooseOne(graphene.ObjectType):
    class Meta:
        interfaces = (SurveyQuestion,)

    type = QuestionType(default_value=QuestionType.CHOOSE_ONE, required=True)
    options = graphene.List(graphene.String, required=True)
    choice = graphene.Int()
    followUps = graphene.List(FollowUp, default_value=[])

    @staticmethod
    def resolve_type(parent, info):
        return QuestionType.CHOOSE_ONE


class FreeResponse(graphene.ObjectType):
    class Meta:
        interfaces = (SurveyQuestion,)

    type = QuestionType(default_value=QuestionType.FREE_RESPONSE, required=True)
    response = graphene.String()

    @staticmethod
    def resolve_type(parent, info):
        # print(type(parent.type))
        return QuestionType.FREE_RESPONSE


class StarCondition(graphene.ObjectType):
    upperBound = graphene.Int(required=True)
    lowerBound = graphene.Int(required=True)


class Star(graphene.ObjectType):
    class Meta:
        interfaces = (SurveyQuestion,)

    type = QuestionType(default_value=QuestionType.STAR, required=True)
    rating = graphene.Float()
    followUps = graphene.Field(FollowUp, default_value={'start': 0, 'length': 0})
    followUpCondition = graphene.List(StarCondition)
    leftHint = graphene.String()
    rightHint = graphene.String()

    @staticmethod
    def resolve_type(parent, info):
        return QuestionType.STAR


class YesNo(graphene.ObjectType):
    class Meta:
        interfaces = (SurveyQuestion,)

    type = QuestionType(default_value=QuestionType.YES_NO, required=True)
    answer = graphene.Boolean()
    yesFollowUps = graphene.Field(FollowUp, default_value={'start': 0, 'length': 0})
    noFollowUps = graphene.Field(FollowUp, default_value={'start': 0, 'length': 0})

    @staticmethod
    def resolve_type(parent, info):
        return QuestionType.YES_NO


class End(graphene.ObjectType):
    class Meta:
        interfaces = (SurveyQuestion,)

    @staticmethod
    def resolve_type(parent, info):
        return QuestionType.END


class Survey(graphene.ObjectType):
    questions = graphene.List(SurveyQuestion, required=True)
    answered = graphene.Int()
    type = graphene.Field(SurveyType, required=True, default_value=SurveyType.FLAT)


class Ingredient(graphene.ObjectType):
    quantity = graphene.Float()
    quantity_obtained = graphene.Float()
    unit = graphene.String()
    name = graphene.String()


class Equipment(graphene.ObjectType):
    name = graphene.String()
    quantity = graphene.Int()


class GroceryList(graphene.ObjectType):
    items = graphene.List(Ingredient)


class Skill(graphene.ObjectType):
    name = graphene.String()
    progress = graphene.Float()


class UserSkills(graphene.ObjectType):
    skills = graphene.List(Skill, default_value=[])


class MicroStep(graphene.ObjectType):
    ingredients = graphene.List(Ingredient, default_value=[])
    equipment = graphene.List(Equipment, default_value=[])
    skills = graphene.List(Skill, default_value=[])
    text = graphene.String()

class ChangeLog(graphene.ObjectType):
    major = graphene.Int()
    minor = graphene.Int()
    patch = graphene.Int()
    build = graphene.Int()
    major_changes = graphene.List(graphene.String, default_value=[])
    minor_changes = graphene.List(graphene.String, default_value=[])
    patch_changes = graphene.List(graphene.String, default_value=[])
    build_changes = graphene.List(graphene.String, default_value=[])


class MacroStep(graphene.ObjectType):
    steps = graphene.List(MicroStep, default_value=[])
    name = graphene.String(default_value='')


class Recipe(graphene.ObjectType):
    recipe_name = graphene.String()
    recipe_id = graphene.Int()
    ingredients = graphene.List(Ingredient)
    equipment = graphene.List(Equipment)
    steps = graphene.List(MacroStep, default_value=[])
    thumbnail_url = graphene.String()
    splash_url = graphene.String()
    time_estimate = graphene.Int()
    description = graphene.String()

    # @staticmethod
    # def resolve_ingredients(parent, info):
    #     recipe_id = parent["recipe_id"]
    #     query = f'MATCH (:Recipe {{recipe_id: {recipe_id}}})-[c:IngredientIn]-(i:Ingredient) RETURN i, c'
    #     results = get_db().run(query)
    #     ingredients = []
    #     for record in results:
    #         ingredient = unpack(record.get("i"))
    #         connection = unpack(record.get("c"))
    #         if "quantity" in connection:
    #             ingredient["quantity"] = connection["quantity"]
    #         if "unit" in connection:
    #             ingredient["unit"] = connection["unit"]
    #         ingredients.append(ingredient)
    #     return ingredients


class Menu(graphene.ObjectType):
    recipes = graphene.List(Recipe, default_value=[])
    menu_index = graphene.Int()


class Menus(graphene.ObjectType):
    menus = graphene.List(Menu, default_value=[])


class AccountFlags(graphene.ObjectType):
    completed_orientation = graphene.Boolean(default_value=False)
    verified = graphene.Boolean(default_value=False)


class Account(graphene.ObjectType):
    name = graphene.String()
    session = graphene.String()
    email = graphene.String()
    dietary_restrictions = graphene.List(graphene.String)
    grocery_list = graphene.Field(GroceryList)
    equipment = graphene.List(Equipment)
    menus = graphene.List(Menu)
    meals_made = graphene.Int()
    mastered_skills = graphene.Int()
    skills = graphene.List(Skill)
    account_flags = graphene.Field(AccountFlags)

    @staticmethod
    def resolve_name(parent, info):
        return parent["name"]

    @staticmethod
    def resolve_menus(parent, info):
        params = {'session': parent['session']}
        check_menus_query = '''MATCH (a:Account {session: $session})-[]-(m: Menu)
                     CALL {
                        WITH m MATCH (m)-[]-(r:Recipe) RETURN COLLECT(r) as recipe_list
                     }
                     RETURN m, recipe_list'''
        results = get_db().run(check_menus_query, parameters=params)
        menus = []
        for record in results:
            menu = unpack(record.get('m'))
            # print(record.get('list'))
            recipes = [json.loads(recipe['json']) if recipe['json'] is not None else unpack(recipe) for recipe in
                       record.get('recipe_list')]
            # print(recipes)
            menu['recipes'] = recipes
            # print(menu)
            menus.append(menu)

        print(menus)

        return menus

    @staticmethod
    def resolve_mastered_skills(parent, info):
        session = parent['session']
        query = f'MATCH (a:Account {{session: "{session}"}})-[:HasSkill {{progress' \
                f': 1}}]-(s:Skill) RETURN count(s) as count'
        results = get_db().run(query)
        record = results.single()
        mastered_skills = record.get("count") if not None else 0
        return mastered_skills

    @staticmethod
    def resolve_meals_made(parent, info):
        session = parent['session']
        query = f'MATCH (a:Account {{session: "{session}"}})-[c:Made]-(r:Recipe) RETURN count(c) as meals_made'
        results = get_db().run(query)
        record = results.single()
        meals_made = record.get("meals_made") if not None else 0
        print(meals_made)
        return meals_made

    @staticmethod
    def resolve_skills(parent, info):
        session = parent['session']
        params = {'session': session}
        query = 'MATCH (a:Account {session: $session}),(s:Skill) OPTIONAL MATCH (a)-[c:HasSkill]->(s) RETURN ' \
                'COALESCE(c.progress, 0) as progress, s.name as name'
        results = get_db().run(query, parameters = params)
        skills = {}
        for record in results:
            d = {"progress": record.get("progress") if not None else 0, "name": record.get("name")}
            if "progress" not in d:
                d['progress'] = 0
            skills[d['name']] = d
            # print(d)

        get_completed_recipe_skills = '''MATCH (a:Account {session: $session}),
            (a)-[c:Made]->(r: Recipe)
            WITH a, c, r CALL {
                WITH a, c, r
                UNWIND r.skills as skill
                RETURN skill
            }
            RETURN skill , count(skill) as skill_count
        '''

        results = get_db().run(get_completed_recipe_skills, parameters= params)
        for record in results:
            count = record.get("skill_count")
            print(record)
            skill_name = record.get("skill")
            print(f"count: {count}, skill: {skill_name}")
            if count is not None:
                skills[skill_name]["progress"] = min(count / 7, 1)
        # print(list(skills.values()))
        # user_skills = {'skills': list(skills.values())}

        return list(skills.values())

    @staticmethod
    def resolve_flags(parent, info):
        session = parent['session']
        query = f'MATCH (a: Account{{session: "{session}"}})-[]->(flags: Flags) RETURN flags'
        results = get_db().run(query)
        print("Getting account flags")
        flags = {}
        for record in results:
            flags = unpack(record.get('flags'))

        return flags


def unpack(iterable):
    results = {}
    for res in iterable:
        results[res] = iterable[res]

    return results


class Query(graphene.ObjectType):
    hello = graphene.String(name=graphene.String(default_value="stranger"))
    random = graphene.Float()
    goodbye = graphene.String()
    menu = graphene.List(Menu, num_menus=graphene.Int(default_value=1))
    account = graphene.Field(Account, required=True, session=graphene.String())
    presign_object = graphene.String(key=graphene.String(required=True))
    survey = graphene.Field(Survey, survey_string=graphene.String(required=False))
    recipe = graphene.Field(Recipe, recipe_id=graphene.Int(required=True))
    change_log = graphene.List(ChangeLog, app_version=graphene.String(required=True))

    @staticmethod
    def resolve_recipe(parent, info, recipe_id):
        query = "MATCH (r: Recipe {recipeId: toInteger($recipe_id)}) RETURN r.json AS recipe LIMIT 1"
        results = get_db().run(query, parameters=({'recipe_id': recipe_id}))
        recipe = None
        for item in results:
            recipe = item.get('recipe')
        return json.loads(recipe)

    @staticmethod
    def resolve_survey(root, info, survey_string=None):
        if survey_string is not None:
            print(survey_string)
            json_repr = json.loads(survey_string)
            print(json_repr)
            return json_repr
        free_response = FreeResponse(title="This is a free response question", response="This is the serialized "
                                                                                        "response :)")
        yes_no = YesNo(title="This is a yes or no question", answer=True)

        return Survey(questions=[free_response, yes_no])

    @staticmethod
    def resolve_hello(root, info, name):
        return f'Hello {name}'

    @staticmethod
    def resolve_goodbye(root, info):
        return 'See ya!'

    @staticmethod
    def resolve_random(root, info):
        return random.random()

    @staticmethod
    def resolve_menu(parent, info, num_menus):
        return [Menu()] * num_menus

    @staticmethod
    def resolve_presign_object(parent, info, key):
        signed_url = presign_object(key=key)
        print(signed_url)
        return signed_url

    @staticmethod
    def resolve_account(parent, info, session):
        results = get_db().run(f'MATCH (account:Account {{session: "{session}"}}) RETURN account LIMIT 1')
        record = None
        for record in results:
            print(record)
        return unpack(record.get("account"))

    @staticmethod
    def resolve_change_log(parent, info, app_version):
        return AppChangeLog().get_since(app_version)


class ScreenChangeMetric(graphene.InputObjectType):
    start_time = graphene.DateTime(required=True)
    screen_duration = graphene.Float(required=True)
    start_screen = graphene.String(required=True)
    next_screen = graphene.String(required=True)
    session_id = graphene.String(required=True)


class SubmitScreenChangeMetrics(graphene.Mutation):
    class Arguments:
        screen_change_metrics = graphene.List(ScreenChangeMetric, required=True)

    ok = graphene.Boolean(required=True)

    @staticmethod
    def mutate(root, info, screen_change_metrics):
        # Do something with the screen change metrics
        print(screen_change_metrics)
        ok = True
        return SubmitScreenChangeMetrics(ok=ok)


class PasswordForm(graphene.InputObjectType):
    email = graphene.String(required=True)
    name = graphene.String(required=True)
    password_input = graphene.String(required=True)


class Login(graphene.Mutation):
    class Arguments:
        email = graphene.String(required=True)
        password_input = graphene.String(required=True)

    ok = graphene.Boolean(required=True)
    session = graphene.String()
    account = graphene.Field(Account)

    @staticmethod
    def mutate(root, info, email, password_input):
        print("Fulfilling login request")
        password_from_db_query = f'MATCH (a:Account {{email: "{email}"}}) RETURN a LIMIT 1'
        results = get_db().run(password_from_db_query)
        account = None
        for record in results:
            account = unpack(record.get("a"))
        if account is None:
            print("Account doesn't exist")
            return Login(ok=False)

        if not compare_password(account['password'], password_input):
            print("Password does not match")
            return Login(ok=False)

        session = uuid.uuid4().hex

        update_session_query = f'MATCH (a:Account {{email: "{email}"}})-[:HasFlags]->(f: Flags) SET a.session = "{session}" ' \
                               f'RETURN a, f '
        results = get_db().run(update_session_query)
        for record in results:
            account = unpack(record.get("a"))
            account['accountFlags'] = unpack(record.get("f"))
            print(f"flags: {unpack(record.get('f'))}")

        print(f'Logged in account {account}')
        return Login(account=account, ok=True, session=session)


class Logout(graphene.Mutation):
    class Arguments:
        session = graphene.String(required=True)

    ok = graphene.Boolean(required=True)

    @staticmethod
    def mutate(root, info, session):
        query = f'MATCH (a:Account {{session: "{session}"}}) SET a.session = null RETURN a'
        results = get_db().run(query)
        print(results)
        account = None
        for record in results:
            account = unpack(record.get("a"))
        return Logout(ok=(account is not None))


def account_exists(email: str) -> bool:
    query = f'MATCH (a:Account {{email: "{email}"}}) RETURN a'
    results = get_db().run(query)
    records = 0
    for _ in results:
        records += 1
    exists = False if records == 0 else True
    return exists


def password_valid(p: str) -> bool:
    if len(p) < 8:
        return False
    return True


class CompleteRecipe(graphene.Mutation):
    class Arguments:
        recipe_id = graphene.Int(required=True)
        session = graphene.String(required=True)

    ok = graphene.Boolean(required=True)

    @staticmethod
    def mutate(root, info, recipe_id, session, **kwargs):
        params = {'session': session, 'recipe_id': recipe_id}
        query = '''MATCH (a: Account {session: $session}), (r: Recipe {recipeId: $recipe_id})
        CREATE (a)-[c:Made {time: datetime.realtime()}]->(r)
        RETURN c
        '''

        results = get_db().run(query, parameters=params)
        record = None
        for record in results:
            pass
        ok = False if record is None else True

        return CompleteRecipe(ok=ok)


class CreateAccount(graphene.Mutation):
    class Arguments:
        password_form = PasswordForm(required=True)

    ok = graphene.Boolean(required=True)
    code = graphene.String()
    session = graphene.String()
    account = graphene.Field(Account)

    @staticmethod
    def mutate(root, info, password_form):
        print(password_form)
        email = password_form['email']
        password_input = password_form['password_input']
        name = password_form['name']
        if account_exists(email):
            return CreateAccount(ok=False, code="Error: Account with that email already exists")
        if not password_valid(password_form['password_input']):
            return CreateAccount(ok=False, code="Error: Invalid password format")
        password_hash = create_password(password_input)
        # print(f'Name: {name}, Email: {email}, Password: {password}')

        session = uuid.uuid4().hex
        create_account_query = f'CREATE (a:Account {{email: "{email}", name: "{name}", password: "{password_hash}", ' \
                               f'session: "{session}", verified: false, completedOrientation: false}}), (f:Flags),' \
                               f'(a)-[c:HasFlags]->(f) return a, c, f'

        results = get_db().run(create_account_query)
        account = None
        for record in results:
            account = unpack(record.get("a"))

        return CreateAccount(ok=True, code="", session=session, account=account)


def upload_to_s3(file: FileStorage, prefix: str = 'images', bucket: str = BUCKET) -> Tuple[bool, str, str]:
    key, local_file = save_file(file)

    ok, name = upload_file(key=f'{prefix}/{key}', filename=local_file, bucket=bucket)

    if ok:
        os.remove(local_file)

    return ok, name, bucket


class Post(graphene.Mutation):
    class Arguments:
        file = Upload(required=True)
        caption = graphene.String(required=True)
        session = graphene.String(required=True)
        public = graphene.Boolean(required=True)
        recipe_id = graphene.Int(required=False, default_value=-1)

    ok = graphene.Boolean(required=True)

    @staticmethod
    def mutate(self, info, file: FileStorage, caption: str, public: bool, session: str, recipe_id, **kwargs):
        # TODO upload file to S3, create a Post node with the image access url and caption,
        #   and then link to the person with the given session
        ok, key, bucket = upload_to_s3(file, prefix='social_posts')
        if not ok:
            return Post(ok=False)

        params = {'session': session, 'caption': caption, 'public': public, 'key': key, 'bucket': bucket,
                  'recipe_id': recipe_id}
        query = '''MATCH (a: Account {session: $session}), (r: Recipe {recipeId: $recipe_id})
        CREATE (p: Post {caption: $caption, key: $key, bucket: $bucket, public: $public, time: datetime.realtime()}),
        (a)-[c1:MadePost {time: datetime.realtime(), public: $public}]->(p),
        (p)-[c2:AboutRecipe]->(r)
        RETURN p
        '''
        results = get_db().run(query, parameters=params)
        record = None
        for record in results:
            continue
        ok = False if record is None else True

        return Post(ok=ok)


class UploadFile(graphene.Mutation):
    class Arguments:
        file = Upload(required=True)

    ok = graphene.Boolean(required=True)

    @staticmethod
    def mutate(parent, info, file: FileStorage, **kwargs):
        print(file)
        print(type(file))
        # do something with your graphene_file_upload
        # key, local_file = save_file(file)
        #
        # ok, name = upload_file(key=key, filename=local_file)
        #
        ok, key, bucket = upload_to_s3(file)
        # upload_time = "{date:%Y-%m-%d_%H:%M:%S}".format(date=datetime.datetime.now())
        # file.save(f'{file_hash}-{upload_time}.img')
        # with open(f'{file_hash}-{upload_time}', 'wb') as output_file:
        #     output_file.write(file)
        return UploadFile(ok=ok)


class UploadSurvey(graphene.Mutation):
    class Arguments:
        survey = graphene.String(required=True)
        session = graphene.String(required=True)

    ok = graphene.Boolean(required=True)

    @staticmethod
    def mutate(parent, info, survey, session, **kwargs):
        print(json.loads(survey))
        # TODO tie this to the user's account somehow
        now = datetime.now()
        prefix = f'survey/{now.strftime("%Y-%m-%d")}'
        survey_dump = json.dumps({'session': session, 'survey': survey, 'time': now.strftime("%Y-%m-%d %H:%M:%S")})
        survey_hash = hash(survey)
        key = f'{prefix}/{session}/{survey_hash}'
        ok, key = upload_object(key=key, content=survey_dump)
        print(key)
        return UploadSurvey(ok=ok)


class SetFlag(graphene.Mutation):
    class Arguments:
        session = graphene.String(required=True)
        flag = graphene.String(required=True)
        value = graphene.Boolean(required=False, default_value=True)

    ok = graphene.Boolean(required=True)
    flags = graphene.Field(AccountFlags)

    @staticmethod
    def mutate(parent, info, session, flag, value, **kwargs):
        query = f'MATCH (a:Account {{"session": {session}}})-[]->(flags:Flags) SET a.{flag} = {value}, return flags'
        results = get_db().run(query)
        flags: dict = {}
        for record in results:
            flags = unpack(record.get('flags'))
        ok = True
        if len(flags) == 0:
            ok = False
        return SetFlag(ok=ok, flags=flags)

#
# class RequestMenuTest(graphene.Mutation):
#         class Arguments:
#             recipe_count = graphene.Int()
#             menu_count = graphene.Int()
#
#         ok = graphene.Boolean()
#         menus = graphene.List(graphene.List(graphene.Int))
#
#         @staticmethod
#         def mutate(parent, info, recipe_count, menu_count, **kwargs):
#             params = {"recipe_count": recipe_count, "menu_count": menu_count,}
#             query = '''UNWIND range(1, $menu_count) as menu_index
#                 WITH menu_index CALL {
#                    MATCH (r:Recipe) WHERE toInteger(r.recipeId) < 1000
#                    RETURN r.json as recipe, r.recipeId as recipe_id ORDER BY rand() LIMIT $recipe_count
#                 }
#                 WITH menu_index, recipe, recipe_id CALL {
#                     WITH recipe, recipe_id
#                     RETURN collect(recipe) as recipes, collect(recipe_id) as recipe_ids
#                 }
#                 RETURN menu_index, recipes, recipe_ids'''
#             recipes = []
#             recipe_ids = []
#             results = get_db().run(query, parameters=params)
#             for record in results:
#                 recipes.extend(record.get('recipes'))
#                 # print(f'Number of recipe lists: {len(recipes)}')
#                 # print(f"Number of recipes in each list: {len(record.get('recipes'))}")
#                 recipe_ids.extend(record.get('recipe_ids'))
#                 # print(type(recipes[0]))
#                 # print(record.get('menu_index'))
#             # print(recipes)
#             # recipe_ids = [json.loads(recipe)['recipe_id'] for recipe in recipes]
#
#             menu_params = {'recipe_ids': recipe_ids, 'menu_count': menu_count}
#             print(recipe_ids)
#             assign_query = '''
#                 UNWIND range(1, $menu_count) AS menu_index
#                 WITH $recipe_ids[menu_index] as recipe_ids, menu_index
#                 CALL {
#                     WITH recipe_ids
#                     UNWIND recipe_ids AS id
#                     OPTIONAL MATCH (r:Recipe {recipeId: toInteger(id)})
#                     RETURN COLLECT(r) AS recipes
#                 }
#                 WITH recipes, menu_index
#                 RETURN recipes, menu_index
#             '''
#             print(menu_params)
#             results = get_db().run(assign_query, parameters=menu_params)
#             menus = []
#             for record in results:
#                 menu = {}
#                 print(record.get('menu_index'))
#                 # print(record.get('recipes'))
#                 # recipes = [json.loads(recipe['json']) if recipe['json'] is not None else unpack(recipe) for recipe in
#                 #            record.get('recipes')]
#                 # print(len(recipes))
#                 # menu['recipes'] = [json.loads(recipe) for recipe in recipes[len(menus):len(menus) + recipe_count]]
#                 menu['recipe_ids'] = [json.loads(recipe)['recipe_id'] for recipe in recipes[len(menus) * recipe_count:(len(menus) + 1) * recipe_count]]
#                 menus.append(menu)
#             print(menus)
#             return RequestMenuTest(ok=True, menus=menus)
#


class RequestMenu(graphene.Mutation):
    class Arguments:
        recipe_count = graphene.Int()
        menu_count = graphene.Int()
        session = graphene.String(required=True)
        override = graphene.Boolean()

    ok = graphene.Boolean()
    menus = graphene.List(Menu)

    @staticmethod
    def mutate(parent, info, recipe_count, menu_count, session, override, **kwargs):
        # TODO create a request menu mutation
        params = {"recipe_count": recipe_count, "menu_count": menu_count, "session": session}
        if not override:
            check_menus_query = '''MATCH (a:Account {session: $session})-[]-(m: Menu)
             CALL {
                WITH m MATCH (m)-[]-(r:Recipe) RETURN COLLECT(r) as list
             }
             RETURN m, list'''
            results: neo4j.Result = get_db().run(check_menus_query, parameters=params)
            menus = []
            for record in results:
                menu = unpack(record.get('m'))
                # print(record.get('list'))
                recipes = [json.loads(recipe['json']) if recipe['json'] is not None else unpack(recipe) for recipe in
                           record.get('list')]
                # print(recipes)
                menu['recipes'] = recipes
                # print(menu)
                menus.append(menu)

            # print(menus)
            if len(menus) > 0:
                return RequestMenu(ok=True, menus=menus)
        print(menu_count)
        query = '''UNWIND range(1, $menu_count) as menu_index
                WITH menu_index CALL {
                   MATCH (r:Recipe) WHERE toInteger(r.recipeId) < 1000
                   RETURN r.json as recipe, r.recipeId as recipe_id ORDER BY rand() LIMIT $recipe_count
                }
                WITH menu_index, recipe, recipe_id CALL {
                    WITH recipe, recipe_id
                    RETURN collect(recipe) as recipes, collect(recipe_id) as recipe_ids
                }
                RETURN menu_index, recipes, recipe_ids'''
        recipes = []
        recipe_ids = []
        results = get_db().run(query, parameters=params)
        for record in results:
            recipes.extend(record.get('recipes'))
            # print(f'Number of recipe lists: {len(recipes)}')
            # print(f"Number of recipes in each list: {len(record.get('recipes'))}")
            recipe_ids.extend(record.get('recipe_ids'))
            # print(type(recipes[0]))
            # print(record.get('menu_index'))
        # print(recipes)
        # recipe_ids = [json.loads(recipe)['recipe_id'] for recipe in recipes]

        menu_params = {'recipe_ids': recipe_ids, 'menu_count': menu_count, 'session': session}
        print(recipe_ids)
        assign_query = '''MATCH (a: Account {session: $session})
            WITH a
            UNWIND range(1, $menu_count) AS menu_index
            CREATE (m: Menu {menu_index: menu_index, time: datetime.realtime()}), (a)-[c:HasMenu]->(m)
            WITH a, m, $recipe_ids[menu_index] as recipe_ids
            CALL {
                WITH m, recipe_ids
                UNWIND recipe_ids AS id
                OPTIONAL MATCH (r:Recipe {recipeId: toInteger(id)})
                CREATE (m)-[c:HasRecipe]->(r)
                RETURN COLLECT(r) AS recipes
            }
            RETURN m, recipes
        '''
        results = get_db().run(assign_query, parameters=menu_params)
        menus = []
        for record in results:
            menu = unpack(record.get('m'))
            # print(record.get('recipes'))
            # recipes = [json.loads(recipe['json']) if recipe['json'] is not None else unpack(recipe) for recipe in
            #            record.get('recipes')]
            # print(len(recipes))
            menu['recipes'] = [json.loads(recipe) for recipe in recipes[len(menus) * recipe_count:(len(menus) + 1) * recipe_count]]
            menus.append(menu)
        print(menus)
        return RequestMenu(ok=True, menus=menus)


class UploadRecipeImage(graphene.Mutation):
    class Arguments:
        image = Upload(required=True)
        recipe_id = graphene.Int(required=True)
        session = graphene.String(required=True)

    ok = graphene.Boolean(required=True)

    @staticmethod
    def mutate(parent, info, image, recipe_id, session, **kwargs):
        ok, key, bucket = upload_to_s3(image)
        if not ok:
            return UploadRecipeImage(ok=ok)

        params = {'bucket': bucket, 'key': key, 'recipe_id': recipe_id, 'session': session}
        query = '''MATCH (a: Account {session: $session}), (r: Recipe {recipeId: $recipe_id})
        CREATE (node: RecipeImage {key: $key, bucket: $bucket}),
        (a)-[c1:TookPicture{time: datetime.realtime()}]->(node),
        (node)-[c2:PictureOf]->(r)
        RETURN node;
        '''
        results = get_db().run(query, parameters=params)

        record = None
        for record in results:
            continue

        ok = False if record is None else True
        return UploadRecipeImage(ok=ok)


class UploadFeedback(graphene.Mutation):
    class Arguments:
        file = Upload(required=True)
        description = graphene.String(required=True)
        tags = graphene.List(graphene.String, default_value=[])
        feedback_type = graphene.String(required=True)
        state = graphene.String(required=True)
        session = graphene.String()

    ok = graphene.Boolean(required=True)

    @staticmethod
    def mutate(parent, info, file, description, tags, feedback_type, state, session, **kwargs):
        # TODO: Upload the screenshot to S3 and then create a json file to represent the
        #       the data that was reported as a result, including the time of upload
        print('Received feedback!')
        ok, key, bucket = upload_to_s3(file)
        if not ok:
            return UploadFeedback(ok=False)

        now = datetime.now()
        prefix = f'feedback/{now.strftime("%Y-%m-%d")}'

        feedback_dict = {'key': key, 'bucket': bucket, 'description': description,
                         'time': now.strftime("%Y-%m-%d %H:%M:%S"), 'tags': tags, 'state': state,
                         'feedbackType': feedback_type, 'session': session}

        suffix = hash(hash(description) + hash(now))
        feedback_json_key = f'{prefix}/{suffix}.json'
        feedback_json = json.dumps(feedback_dict)
        # print(feedback_json)
        # print(feedback_json_key)
        s3_tags = [f'type={feedback_type}']
        s3_tags.extend(tags)

        ok, key = upload_object(key=feedback_json_key, content=feedback_json, tags=s3_tags)

        return UploadFeedback(ok=ok)


class Mutations(graphene.ObjectType):
    submit_screen_change_metrics = SubmitScreenChangeMetrics.Field()
    create_account = CreateAccount.Field()
    login = Login.Field()
    logout = Logout.Field()
    upload = UploadFile.Field()
    upload_survey = UploadSurvey.Field()
    set_flag = SetFlag.Field()
    request_menus = RequestMenu.Field()

    upload_feedback = UploadFeedback.Field()
    post = Post.Field()
    upload_recipe_image = UploadRecipeImage.Field()
    complete_recipe = CompleteRecipe.Field()


# noinspection PyTypeChecker
schema = graphene.Schema(query=Query, mutation=Mutations, types=[FreeResponse, YesNo, Star, StarCondition, ChooseOne,
                                                                 ChooseMany, QuestionType, End])
