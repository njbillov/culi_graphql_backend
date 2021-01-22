import os
from json import dumps
from flask import Flask, g, Response, request

from neo4j import GraphDatabase, basic_auth

app = Flask(__name__)

url = "bolt://localhost"
password = 'memphis-place-optimal-velvet-phantom-127'

driver = GraphDatabase.driver(url,auth=basic_auth("neo4j", password),encrypted=False)

def get_db():
    if not hasattr(g, 'neo4j_db'):
        g.neo4j_db = driver.session()
    return g.neo4j_db
