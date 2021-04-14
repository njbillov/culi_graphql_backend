## Table of Contents
* [Setup](#Setup)
* [Database](#Database)
* [GraphQL](#GraphQL)
* [Recipe Parser](#Recipe-Parser)
* [Recipe Updater](#Recipe-Updater)

### Setup
1) Get your computer setup with the AWS-CLI with an account that has PUT/GET permissions with S3.
1) Download this repository
1) Run scripts/download_config
1) Install and start an instance of neo4j (only validated for >=4.1.3). Make sure that the URI and passwords for it are stored correctly in .db_uri and .db_password (these files are not included are automatically fetched in scripts/download_config)
1) Create a new env and `pip install -r requirements.txt`
1) Load recipes into your neo4j instance with `./recipe_loader.py add ./recipes`
1) `./graph.py` to start the flask server locally

### Database
Neo4j was chosen as the database for this application because of its ability to simplify recommendation algorithms and analytics in the future.  At the present time, none of those specific advantages are used.  So, instead of using a more connected way of representing recipes, the json is just dumped into neo4j so it can be conveniently exported view GraphQL.

### GraphQL Endpoint
All of the client interactions with the backend go through the GraphQL endpoint to communicate with the neo4j instance.  To accomplish any account actions, the client provides a session token to verify the account and this reduces the number of roundtrips before the client gets all their data.

### Recipe Parser
The recipe parser's main purpose is to handle adding, updating, and deleting recipes from the database.  It can be used as a standalone command line tool or called directly or used directly in the web server.

### Recipe Updater
The recipe updater is a Google Sheets interface + a few extra web pages on the web server to handle recipe updates without needing to ssh into the server.  To make the updater website simpler to create, all the pages are just statically rendered and clicking buttons do not give feedback, but do make an effect on the database.



