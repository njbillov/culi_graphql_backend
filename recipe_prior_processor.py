#!venv/bin/python

import ast
import json

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer


def main():
    df = pd.read_csv("RAW_recipes.csv")

    ingredient_counts = df['ingredients'].dropna().apply(ast.literal_eval).explode().value_counts()

    with open("ingredient_counts.json", "w") as file:
        file.write(ingredient_counts.to_json(indent=4))
    print("Wrote out ingredient counts to disk")

    step_words = df['steps'].dropna().apply(ast.literal_eval).explode().dropna()

    model = CountVectorizer(ngram_range=(1, 1), min_df=10)

    training = model.fit_transform(step_words)

    frequencies = np.array(training.sum(axis=0)).flatten()
    pairs = dict(zip(model.get_feature_names(), frequencies.tolist()))

    with open("step_word_counts.json", "w") as file:
        file.write(json.dumps(pairs, indent=4))
    print("Wrote out step word frequencies to disk")


if __name__ == '__main__':
    main()
