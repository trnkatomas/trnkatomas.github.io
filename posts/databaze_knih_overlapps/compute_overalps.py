import json
import pandas as pd
import itertools

#!cat databaze_knih_log.ndjson | grep "^{" > clean_databaze_knih_log.ndjson

df = pd.read_json('clean_databaze_knih_log.ndjson', lines=True)

# Group reviewers by book
book_users = df.groupby(['book_title', 'author']).agg(users=('user_name', set),
                                                      user_reviews=('user_name', 'count')).reset_index()

# 3. Format for JS (Nodes and Edges)
nodes = []
for i, book in book_users.iterrows():
    nodes.append({
        "id": i,
        "label": book['book_title'],
        "title": f"Author: {book['author']}\nTotal Reviewers: {book['user_reviews']}"
    })

edges = []
# Calculate pairwise overlap
for book_a, book_b in itertools.combinations(book_users.book_title.values, 2):
    book_a_df = book_users[book_users.book_title==book_a]
    book_b_df = book_users[book_users.book_title==book_b]
    if book_a_df.empty or book_b_df.empty:
        continue
    overlap = len(book_b_df.users.values[0] & book_a_df.users.values[0])
    
    # We only create an edge if there is at least some overlap
    if overlap > 0:
        edges.append({
            "from": int(book_a_df.index.values[0]),
            "to": int(book_b_df.index.values[0]),
            "value": overlap, # Thickness in JS
            "title": f"{overlap} shared reviewers between '{book_a}' and '{book_b}'"
        })

# 4. Save to JSON file
final_output = {
    "nodes": nodes,
    "edges": edges
}

with open('book_overlap_graph.json', 'w', encoding='utf-8') as f:
    json.dump(final_output, f, ensure_ascii=False, indent=4)

print("\nSuccess! Generated 'book_overlap_graph.json'.")

import seaborn as sns
import numpy as np
import matplotlib.pyplot as plt
import json

data = json.load(open("book_overlap_graph.json"))
labels = [x['label'] for x in data['nodes']]

len(labels)

hm = np.zeros(shape=(len(labels), len(labels)))
for x in data['edges']:
    hm[x['from'], x['to']] = x['value']

hm = hm + hm.T

sns.heatmap(np.log10(hm), yticklabels=labels, xticklabels=labels)

# comparison
all_overlapping_users = df.groupby('user_name').agg({'book_title':'nunique'}).reset_index()
review_a_lot = all_overlapping_users.sort_values(by='book_title', ascending=False).query('book_title > 10')

better_users = df[df.user_name.isin(review_a_lot.user_name)].groupby('book_title').agg(avg_stars=('stars', 'mean'), unique_users=('user_name', 'nunique'))
all_users = df.groupby('book_title').agg(avg_stars=('stars', 'mean'))

combined = (pd.merge(all_users, better_users, on='book_title', suffixes=['_all_users', '_users_with_context'])
              .reset_index()
              .assign(rating_diff=lambda x: x.avg_stars_all_users - x.avg_stars_users_with_context)
              )

for_plot = pd.melt(combined.reset_index(), id_vars=['book_title'])
sns.barplot(for_plot, y='book_title', x='value', hue='variable')

def draw_a_lot_samples(df, book_name, n_samples, n_test):
    df_book_selection = df[df.book_title == book_name]
    avgs = [df_book_selection.sample(n_samples).groupby('book_title').agg({'stars': 'mean'}).reset_index().stars[0] for i in range(n_test)]
    flat_avgs = np.stack(avgs)
    return flat_avgs

def monte_carlo_permutation_test(combined, df, book, p_value):
    n_tests = 1000
    book_row = combined[combined.book_title == book]
    n_samples = book_row.unique_users.values[0]
    flat_avgs = draw_a_lot_samples(df, book, n_samples=n_samples, n_test=n_tests)
    diff = book_row.rating_diff.values[0]
    diffs = book_row.avg_stars_all_users.values[0] - flat_avgs
    if diff > 0:
        fulfilling_condition = np.sum(diffs >= diff) 
    else:
        fulfilling_condition = np.sum(diffs <= diff)
    percentage = fulfilling_condition/n_tests
    
    # if True, reject null-hypothesis - i.e. the selection is statistically significant
    return percentage, percentage < p_value


    
tested = combined.assign(test_result=lambda x: x.book_title.apply(lambda y: monte_carlo_permutation_test(combined, df, y, 0.05)))

# TODO/check
# * implement the chi-squared test of a good fit - comparing the contingency tables for both the filtered and unfiltered values
# probably do something about the big samples - cause otherwise everything will be significant    
# * https://en.wikipedia.org/wiki/Chi-squared_test
# * https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.permutation_test.html