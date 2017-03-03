from leaderboard import app, load_config
from pymongo import MongoClient
import pytz

load_config('datasets.toml')
app.client = MongoClient()
app.coll = app.client['competition']['results']
app.timezone = pytz.timezone('America/Chicago')

if __name__ == 'main':
    app.run()
