import html
import json
import re
from sheets_reader import GoogleSheetsReader

class RecipeParser:
    def __init__(self):
        self.sheets_reader = GoogleSheetsReader()

    def get_recipe_names(self):
        recipe_ids = self.sheets_reader.read_column('recipes', 'Recipe ID')
        recipe_names = self.sheets_reader.read_column('recipes', 'Recipe Name')
        return [{'id': id, 'name': name} for id, name in zip(recipe_ids, recipe_names)]

    def get_recipe(self, recipe_name=None, recipe_id=None):
        index = 1
        if recipe_name is not None:
            recipe_names = self.sheets_reader.read_column('recipes', 'Recipe Name')
            # print(f'Recipe name list: {recipe_names}')
            index = recipe_names.index(recipe_name) + 1
        elif recipe_id is not None:
            recipe_ids = self.sheets_reader.read_column('recipes', 'Recipe ID')
            print(f'Recipe ID list, looking for {recipe_id}: {recipe_ids}')
            # Account for 1 indexing + the header row
            index = recipe_ids.index(str(recipe_id)) + 2

        recipe_data = self.sheets_reader.read_row_from_source('recipes', index, as_dict=True)

        return parse_recipe(recipe_data)


def parse_macro_instructions(instructions):
  # print("Printing instructions")
  # print(instructions)
  macro_list = []
  brace_depth = 0
  for i, c in enumerate(instructions):
    if c == '{': 
      brace_depth += 1
    elif c == '}':
      brace_depth -= 1
    if c == '-' and brace_depth == 0:
      macro_list.append(i)
  macro_list.append(len(instructions))
  macro_instructions = [instructions[macro_list[i] + 1:macro_list[i + 1]].strip() for i in range(0, len(macro_list) - 1)]
  macro_instructions = list(filter(lambda li: len(li) > 5, macro_instructions))
  # print(f'brace depth: {brace_depth}')
  return macro_instructions

def parse_micro_instructions(macro_instruction):
  micro_list = [0]
  brace_depth = 0
  for i, c in enumerate(macro_instruction):
    if c == '{': 
      brace_depth += 1
    elif c == '}':
      brace_depth -= 1
    if c == ',' and brace_depth == 0:
      micro_list.append(i)
  micro_list.append(len(macro_instruction))
  micro_instructions = [macro_instruction[micro_list[i]:micro_list[i + 1]].strip()[1:] for i in range(0, len(micro_list) - 1)]
  micro_instructions = list(filter(lambda li: len(li) > 5, micro_instructions))
  return micro_instructions

def parse_skills(skills):
  return [{'name': skill.strip()} for skill in filter( lambda s: s != "empty", skills.split(','))]

def strip_parentheses(string: str):
  string = string.strip()
  if len(string) == 0: 
    return string
  if string[0] == '(':
    string = string[1:]
  if string[-1] == ')':
    string = string[0: -1]
  return string

def parse_ingredients(ingredients):
  ingredient_list = []
  open_found = 0
  brace_depth = 0
  for i, c in enumerate(ingredients):
    if c == '{': 
      open_found = i
    elif c == '}':
      cluster = ingredients[open_found + 1: i]
      if len(cluster) < 2:
        continue
      tokens = [token.strip() for token in cluster.split(',')]
      if len(tokens) < 3:
        continue
      ingredient_list.append({"name": tokens[0], "quantity": float(tokens[1]), "unit": tokens[2], "new": len(tokens) > 3})

  return ingredient_list

def parse_equipment(ingredients):
  ingredient_list = []
  open_found = 0
  brace_depth = 0
  for i, c in enumerate(ingredients):
    if c == '{': 
      open_found = i
    elif c == '}':
      cluster = ingredients[open_found + 1: i]
      if len(cluster) < 2:
        continue
      # print(cluster)
      tokens = [token.strip() for token in cluster.split(',')]
      if len(tokens) < 2:
        continue
      ingredient_list.append({"name": tokens[0], "quantity": float(tokens[1])})

  return ingredient_list

def parse_instruction_step(instruction):
  token_indices = [0]
  brace_depth = 0
  for i, c in enumerate(instruction):
    if c == '(': 
      brace_depth += 1
    elif c == ')':
      brace_depth -= 1
    if c == ',' and brace_depth == 0:
      token_indices.append(i)

  token_indices.append(len(instruction))
  attributes = [instruction[token_indices[i]:token_indices[i + 1]].strip()[1:] for i in range(0, len(token_indices) - 1)]
  time_estimate = None
  # print(attributes)
  skills = strip_parentheses(attributes[0])
  equipment = strip_parentheses(attributes[1])
  ingredients = strip_parentheses(attributes[2])
  flavor_text = strip_parentheses(attributes[3])
  if len(attributes) >= 5:
    time_estimate = re.sub(r'[^0-9]', '', attributes[4])
    if len(time_estimate) > 0:
      time_estimate = int(time_estimate)
  return {'skills': parse_skills(skills), 'equipment': parse_equipment(equipment), 'ingredients': parse_ingredients(ingredients), 'flavor_text': flavor_text, 'time_estimate': time_estimate}

def parse_all(instructions_list):
  res = []
  for macro_step in parse_macro_instructions(instructions_list):
    micro_steps = []
    for micro_step in parse_micro_instructions(macro_step):
      micro_steps.append(parse_instruction_step(micro_step))
    res.append(micro_steps)
  return res

def get_ingredient_name(ingredient):
  # print(ingredient)
  ##{"s" if float(ingredient["quantity"]) != 1 else ""} of #
  if ingredient["unit"] in ingredient["name"]:
    return f'{ingredient["quantity"]} {ingredient["name"]}'
  return f'{ingredient["quantity"]} {ingredient["unit"]} {ingredient["name"]}'

def get_equipment_name(equipment):
  return f'{equipment["quantity"]} {equipment["name"]}{"s" if float(equipment["quantity"]) != 1 else ""}'

def flavor_text_to_html(ingredients, equipment, flavor_text):
  text = ""
  step_plain_text = ''
  ptr = 0
  # print(ingredients)
  # print(equipment)
  error_message = ''
  try:
    while ptr < len(flavor_text):
      if flavor_text[ptr] == '{':
        forward_ptr = ptr + 1
        while flavor_text[forward_ptr] != '}':
          forward_ptr += 1
        tokens = [token.strip() for token in flavor_text[ptr + 1:forward_ptr].split(',')]
        # print(tokens)
        isIngredient = tokens[0] == 'i'
        ingredient_index = int(tokens[2]) - 1
        plain_text = tokens[1]
        step_plain_text += plain_text
        error_message = f'Tried to find an {"Ingredient" if isIngredient else "Equipment"} at entry index {ingredient_index + 1} of {ingredients if isIngredient else equipment}, to fill ...{flavor_text[ptr - 20:forward_ptr + 20]}...'
        # print(ingredient_index)
        # print(ingredients)
        # print(equipment)
        # print(flavor_text)
        # print(plain_text)
        hover_text = get_ingredient_name(ingredients[ingredient_index]) if isIngredient else f'{equipment[ingredient_index]["name"]} {equipment[ingredient_index]["quantity"]}'
        color = "color:green" if isIngredient else "color:red"
        text += f'<span title="{hover_text}" style="{color};white-space:nowrap;">{plain_text}</span>'
        ptr = forward_ptr + 1
      else:
        text += flavor_text[ptr]
        step_plain_text += flavor_text[ptr]
        ptr += 1
  except IndexError as e:
    print(e)
    raise Exception(error_message)
  return f'<li>{text}</li>', step_plain_text

def print_recipe(micro_step):
  return flavor_text_to_html(micro_step["ingredients"], micro_step["equipment"], micro_step["flavor_text"])

def parse_recipe(recipe_dict, write_to_file=True, display_html=True):
  recipe_id = recipe_dict['Recipe ID']
  instructions_list = recipe_dict['Instructions']
  recipe_name = recipe_dict['Recipe Name']
  blurb = recipe_dict['Blurb']
  parsed_recipe = parse_all(instructions_list)
  ingredients_list = {}
  equipment_list = {}
  steps = []
  skills = set()
  macro_step = None
  micro_step = None
  time_estimate = parsed_recipe[-1][-1]["time_estimate"]
  time_estimate = time_estimate if time_estimate != 0 else None
  recipe_json = {'steps':  [], 'recipe_name': recipe_name, 'description': blurb,\
                 'recipe_id': recipe_id, 'time_estimate': time_estimate, 'tags': {}}

  for header, value in recipe_dict.items():
    if value == 'y' or value == 'n':
        recipe_json['tags'][header.lower()] = True if value == 'y' else False

  try:
    for macro_step in parsed_recipe:
      # print("Formatting next macro step")
      step = []
      micro_step_list = []
      for micro_step in macro_step:
        # print("Formatting next micro step")
        html_text, micro_step["text"] = print_recipe(micro_step)
        step.append(html_text)
        for skill in micro_step["skills"]:
          skills.add(skill["name"])
        for ingredient in micro_step["ingredients"]:
          if ingredient["name"] in ingredients_list and ingredient["new"]:
            current = float(ingredients_list[ingredient["name"]]["quantity"])
            print(current)
            ingredients_list[ingredient["name"]]["quantity"] = float(ingredient["quantity"]) + current
          else:
            ingredients_list[ingredient["name"]] = ingredient
        for equipment in micro_step["equipment"]:
            equipment_list[equipment["name"]] = equipment
        micro_step_list.append(micro_step)
      steps.append(step)
      recipe_json['steps'].append({'steps': micro_step_list, 'name': ''})
    for _, v in equipment_list.items():
      v["quantity"] = f'{v["quantity"]:.2g}'
    for k, v in ingredients_list.items():
      v["quantity"] = f'{v["quantity"]:.2g}'
    recipe_json['equipment'] = list(equipment_list.values())
    recipe_json['ingredients'] = list(ingredients_list.values())
    
    file_recipename = re.sub("\W", "", recipe_json["recipe_name"])
    filename = f'recipes/{file_recipename}_{recipe_json["recipe_id"]}.json'

  except Exception as e:
    print(e)
    # print(micro_step)
    raise Exception(f'Error when formatting step: {micro_step}')

  return recipe_json, f'''
  <h1>{recipe_name}</h1>
  <h4>{time_estimate} minutes</h4>
  <h2>Skills</h2>
  <ul>
    {"".join(["<li><h4>{}</h4></li>".format(skill) for skill in skills])}
  </ul>
  <h2>Ingredient List</h2>
  <ul>
    {"".join(set(["<li><h4>{}</h4></li>".format(get_ingredient_name(ingredient)) for ingredient in ingredients_list.values()]))}
  </ul>
  <h2> Equipment List</h2>
  <ul>
    {"".join(set(["<li><h4>{}</h4></li>".format(get_equipment_name(equipment)) for equipment in equipment_list.values()]))}
  </ul>
  <h2>Instructions</h2>
  <ol>
    {"<br/>".join(f'<li><ol>{"".join(micro_step)}</ol></li>' for micro_step in steps)}
  </ol>
  ''', filename


def main():
    rp = RecipeParser()

    print(rp.get_recipe(recipe_id=4))


    print(rp.get_recipe(recipe_name='Ramen Noodle Stir Fry'))


if __name__ == '__main__':
    main()