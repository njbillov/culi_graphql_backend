from datetime import datetime
import requests
import json
import random
import string

from requests.api import request

endpoint_url = "http://ec2-54-235-235-19.compute-1.amazonaws.com:8080/graphql"

create_account_query = """mutation LambdaCreateAccount($form: PasswordForm!, $restrictions: [String]!) {
        createAccount(passwordForm: $form, restrictions: $restrictions) {
            ok,
            code,
            session
        }
    }
    """

request_menus_query = """mutation LambdaRequestMenus($recipeCount: Int!, $menuCount: Int!, $session: String!, $override: Boolean) {
        requestMenus(recipeCount: $recipeCount, menuCount: $menuCount, session: $session, override: $override) {
          ok
          menus {
            recipes {
              recipeName
              recipeId
              equipment {
                name 
                quantity
              }
              ingredients {
                name
                unit
                quantity
              }
              steps {
              name
                steps {
                  ingredients {
                    name
                    quantity
                    unit
                  }
                  equipment {
                    name
                    quantity
                  }
                  skills {
                    name
                  }
                  text 
                }
              }
              timeEstimate
              description
              thumbnailUrl
              splashUrl
            }
          }
        }
      }
      """

delete_account_query = """mutation LambdaDeleteAccount($session: String!) {
        deleteAccount(session: $session) {
            ok
            code
        }
    }
    """

class Logger:
    def __init__(self):
        self.logs = []
    
    def get_all(self):
        return '\n'.join(self.logs)

    def print(self, s: str):
        print(f'{datetime.now().strftime("%Y/%m/%d %H:%M:%S")}: {s}')
        self.logs.append(str(s))

logger = Logger()

def create_account():
    letters = string.ascii_lowercase
    email = f"{''.join(random.choice(letters) for i in range(16))}@test_account.com"
    username = ''.join(random.choice(letters) for i in range(8))
    password = ''.join(random.choice(letters) for i in range(8))

    variables = {"form": {"email": email, "name": username, "passwordInput": password}, "restrictions": ["vegetarian"]}

    response = requests.post(url=endpoint_url, json=dict(query=create_account_query, variables=variables))

    if response.status_code != 302 and response.status_code != 200:
        if response.status_code < 400:
            logger.print(f'Received unexpected status code {response.status_code} when creating account')
        else:
            logger.print(f'Received failure status code {response.status_code} when creating account')
        return False, None
    data = json.loads(response.text)['data']['createAccount']

    session = data['session']
    ok = data['ok']
    code = data['code']

    if ok:
        logger.print(f"Account successfully created with session: {session}")
    else:
        logger.print(f"Received error the following coded when trying to create the account: {code}")

    return ok, session


def request_menus(session):
    variables = dict(recipeCount=3, menuCount=2, session=session, override=True)

    response = requests.post(url=endpoint_url, json=dict(query=request_menus_query, variables=variables))

    if response.status_code != 302 and response.status_code != 200:
        if response.status_code < 400:
            logger.print(f'Received unexpected status code {response.status_code} when requesting menus')
        else:
            logger.print(f'Received failure status code {response.status_code} when requesting menus')
        return False, []

    data = json.loads(response.text)['data']['requestMenus']
    
    ok = data['ok']
    nested_menus = [dict(name=recipe['recipeName'], id=recipe['recipeId']) for menu in data['menus'] for recipe in menu['recipes']]

    logger.print(f"Suggested {nested_menus} to new account")

    return ok, nested_menus
    

def cleanup_account(session):
    variables = dict(session=session)

    response = requests.post(url=endpoint_url, json=dict(query=delete_account_query, variables=variables))

    if response.status_code != 302 and response.status_code != 200:
        if response.status_code < 400:
            logger.print(f'Received unexpected status code {response.status_code} when cleaning up account')
        else:
            logger.print(f'Received failure status code {response.status_code} when cleaning up account')
        return False

    data = json.loads(response.text)['data']['deleteAccount']

    print(data)

    ok = data['ok']
    code = data['code']


    if ok:
        logger.print("Account successfully cleaned up")
    else:
        logger.print(f"Received the following error code when trying to delete the account: {code}")

    return ok


def main():
    logger.print("-------------------------------------")
    ok = False
    successful = True
    session = None
    
    failureCause = None
    try:
        ok, session = create_account()
    except requests.ConnectionError as exception:
        logger.print("Received connection error when trying to reach server to create account")
        logger.print(exception)
        if failureCause is None:
            failureCause = "Error accessing server"

    except Exception as exception:
        logger.print("Received error while trying to create account")
        logger.print(exception)
        if failureCause is None:
            failureCause = exception

    successful &= ok
    try:
        ok, nested_menus = request_menus(session)
    except requests.ConnectionError as exception:
        logger.print("Received connection error when trying to reach server to request menus")
        logger.print(exception)
        if failureCause is None:
            failureCause = "Error accessing server"

    except Exception as exception:
        logger.print("Received error while trying to request menus")
        logger.print(exception)
        if failureCause is None:
            failureCause = exception

    successful &= ok
    try:
        ok = cleanup_account(session)
    except requests.ConnectionError as exception:
        logger.print("Received connection error when trying to reach server to cleanup account")
        logger.print(exception)
        if failureCause is None:
            failureCause = "Error accessing server"

    except Exception as exception:
        logger.print("Received error while trying to cleanup account")
        logger.print(exception)
        if failureCause is None:
            failureCause = exception

    successful &= ok

    diagnostics = None
    date_string = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
    if successful:
        logger.print(f"All calls successfully executed at {date_string}")
        diagnostics = dict(time=date_string, status="Alive", cause="", logs=logger.get_all())
    else:
        logger.print(f"Something failed when trying to access API at {date_string}")
        diagnostics = dict(time=date_string, status="Dead", cause=failureCause, logs=logger.get_all())

if __name__ == "__main__":
    main()
