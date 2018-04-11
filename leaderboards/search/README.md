Example code for creating a competition. **Under construction!**

## Setup database

```bash
mkdir db
mongod --dbpath db --fork
mongo
> use competition
> db.createCollection('results')
> db.results.createIndex({'netid': 1})
> exit
mongod --shutdown --dbpath db
```

## Run

```bash
mongod --dbpath db --fork
python seed.py
python leaderboard.py
```

Add changes by calling `seed.py` again or run `unit_test.py` and refresh the
leaderboard page.
