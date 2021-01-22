
from query import run_query


def main():
    print(run_query("{ hello }"))

    query_string = '{ hello(name: "GraphQL") }'
    print(run_query(query_string))

    query_string = '{ menu(numMenus: 2) { recipes(numRecipes: 2){ recipeName ingredients {name quantity} }}}'
    print(run_query(query_string))


if __name__ == '__main__':
    main()
