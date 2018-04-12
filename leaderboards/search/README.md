# Search Competition Leaderboard

This folder contains the necessary code for running a search engine
competition using the [metapy][metapy] Python bindings.

In this folder you will find the code required to run the leaderboard
server itself. In the `student-code` folder you can find example student
skeleton code that allows students to experiment with different ranking
functions and use the Gitlab CI system to submit their results to a
leaderboard server. In the `data` folder you can find some example
configuration files that can be used to run the student code to produce
results for submission to the leaderboard server.

# Production Deployment

We have provided a `docker-compose.yml` and a script for deploying to
Microsoft Azure. To use this, you will need to have `docker`,
`docker-machine` and `docker-compose` installed. Refer to the
[docker-compose installation guide][docker-compose] for installing
`docker-compose`.

Once you have the dependencies installed, make sure you update the
`datasets.toml` file to properly refer to the datasets to be used. Then,
update the `cloud-init.txt` file to properly mount your dataset share on
the leaderboard server:

```bash
cp cloud-init.txt.example cloud-init.txt
vim cloud-init.txt
```

With that out of the way, you can create the virtual machine and all of the
containers for the leaderboard in one go with by using our build script:

```bash
azure/create-search-leaderboard.sh Standard_A1_v2
```

with the environment variables defined from the [CLaDS setup guide][clads].
By default, it will listen on the private IP `10.0.0.10`; you can change
this in the script if you would like.

## Updating Configuration

Should you need to update the code/configuration after deployment, simply
edit the files locally and then execute the following command:

```bash
eval $(docker-machine env clads-search-leaderboard)
docker-compose up -d --no-deps --build leaderboard
```

This should rebuild the container on the remote machine and restart the
leaderboard with the new files.

## Adding a Baseline Submission

The leaderboard supports denoting specific submissions as "Baseline"
submissions; this can be used to create a hybrid assignment where the goal
is to beat the baseline solution, but then where extra credit is granted to
top performers on the leaderboard to encourage friendly competition.

To do so, follow the same procedure as for submitting as a student under a
different account on the Gitlab instance (such as under a TA account).
Then, you can flag the submission as a baseline like so:

```bash
eval $(docker-machine env clads-search-leaderboard)
docker-compose exec mongo \
    mongo competition --eval \
    "db.results.update( \
        {'username': 'BASELINE-USERNAME'}, \
        {$set: {'is_baseline': true}}, \
        {'multi': true}
    );"
```

To un-flag submissions, simply change the `true` to `false` in the above
query.

# Local Use
## Set up database

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

[metapy]: https://github.com/meta-toolkit/metapy
[clads]: https://timan-group.github.io/clads/
[docker-compose]: https://docs.docker.com/compose/install/
