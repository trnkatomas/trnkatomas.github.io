import numpy as np
import itertools
import padnas as pd

df = pd.read_json('clean_databaze_knih_log.ndjson', lines=True)

all_users = df.groupby('book_title').agg(avg_stars=('stars', 'mean'))

all_overlapping_users = df.groupby('user_name').agg({'book_title':'nunique'}).reset_index()

review_a_lot = all_overlapping_users.sort_values(by='book_title', ascending=False).query('book_title > 10')

better_users = df[df.user_name.isin(review_a_lot.user_name)].groupby('book_title').agg(avg_stars=('stars', 'mean'), unique_users=('user_name', 'nunique'))

combined[combined.book_title == 'Šifra mistra Leonarda']

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

def draw_a_lot_samples(df, book_name, n_samples, n_test):
         df_book_selection = df[df.book_title == book_name]
         avgs = [df_book_selection.sample(n_samples).groupby('book_title').agg({'stars': 'mean'}).reset_index().stars[0] for i in range(n_test)]
         flat_avgs = np.stack(avgs)
         return flat_avgs


tested = combined.assign(test_result=lambda x: x.book_title.apply(lambda y: monte_carlo_permutation_test(combined, df, y, 0.05)))
