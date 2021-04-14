import neo4j
from neo4j import GraphDatabase, basic_auth
from neo4j.exceptions import ServiceUnavailable
import os

def unpack(node):
    obj = {}
    for key in node:
        obj[key] = node[key]

    return obj

def unpack_list(results, keys=[]):
    result_list = []
    for record in results:
        obj = {}
        for key in keys:
            obj[key] = unpack(record.get(key))

def unpack_single(result, keys=[]):
    obj = {}
    return unpack(result.single())
    


class GraphDB():
    def __init__(self):
        if not os.path.exists('.dev'):
            if os.path.exists('.db_uri'):
                with open('.db_uri', 'r') as file:
                    os.environ['DB_URI'] = file.read().strip()
            if os.path.exists('.db_password'):
                with open('.db_password', 'r') as file:
                    os.environ['DB_PASSWORD'] = file.read().strip()

        url = os.getenv('DB_URI') if os.getenv('DB_URI') is not None else "bolt://localhost"
        password = os.getenv('DB_PASSWORD') if os.getenv('DB_PASSWORD') is not None else 'memphis-place-optimal-velvet-phantom-127'

        self.driver = GraphDatabase.driver(url, auth=("neo4j", password))



    def run(self, query, parameters=dict()):
        print("Trying to run neo4j command")
        result = None
        with self.driver.session() as session:
            result = session.run(query, parameters=parameters)
        return result

    def get_user_skills(self, session):
        query = 'MATCH (a:Account {session: $session}),(s:Skill) OPTIONAL MATCH (a)-[c:HasSkill]->(s) RETURN ' \
                'COALESCE(c.progress, 0) as progress, s.name as name'
        results = self.run(query, parameters = {'session': session})
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

        results = self.run(get_completed_recipe_skills, parameters={'session': session})
        for record in results:
            count = record.get("skill_count")
            print(record)
            skill_name = record.get("skill")
            print(f"count: {count}, skill: {skill_name}")
            if count is not None:
                skills[skill_name]["progress"] = min(count / 7, 1)
        
        print(skills)

        return list(skills.values())


    def close(self):
        print("Closing driver")
        self.driver.close()



db_connection = GraphDB()
