from leaderboard import app, load_config
from pymongo import MongoClient

load_config('datasets.toml')
app.client = MongoClient('mongo')
app.coll = app.client['competition']['results']

if __name__ == 'main':
    app.run()
