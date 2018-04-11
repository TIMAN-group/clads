import csv
import sys
from leaderboard import app, load_config, update_scores
from pymongo import MongoClient

if __name__ == '__main__':
    if len(sys.argv) != 3:
        print("Usage: python {} datasets.toml output.csv".format(sys.argv[0]))
        sys.exit(1)

    load_config(sys.argv[1])
    app.client = MongoClient()
    app.coll = app.client['competition']['results']

    docs = update_scores()

    print("Writing results to {}...".format(sys.argv[2]))
    with open(sys.argv[2], 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['netid', 'rank', 'overall_score'])
        for doc in docs:
            writer.writerow([doc['netid'], doc['rank'], doc['score']])
