import sys
import json
import math
import metapy
import requests
import pytoml
import pytz

from flask import Flask, request, Response, render_template
app = Flask(__name__, static_folder='.', static_url_path='')
from pymongo import MongoClient

def get_username(token):
    try:
        r = requests.get("{}/user".format(app.gitlab_api_url),
                         headers={'PRIVATE-TOKEN': token})
        return r.json()['username']
    except:
        return None

def compute_dset_score(metrics, scores):
    if not scores:
        return -math.inf
    return sum(metric['weight'] * scores[metric['metric']] for metric in metrics)

def update_doc(username):
    """
    Creates a single row entry for the results table.
    """
    docs = list(app.coll.find({'username': username}).sort([('_id', -1)]).limit(2))
    doc = docs.pop(0)
    doc['num_submissions'] = app.coll.count({'username': username})
    prev_doc = None
    if len(docs) > 0:
        prev_doc = docs.pop(0)
    gen_time = doc['_id'].generation_time.astimezone(app.timezone)
    doc['last_run'] = gen_time.strftime('%Y-%m-%d | %H:%M:%S')
    overall_score, overall_prev = 0.0, 0.0
    for dset, vals in doc['dataset_scores'].items():
        dset_score = compute_dset_score(app.metrics[dset], vals['score'])
        overall_score += dset_score * app.weight[dset]
        doc['dataset_scores'][dset]['prev_score'] = {metric['metric']:
                -math.inf for metric in app.metrics[dset]}
        # If there was an error, show error text instead of -inf score.
        if vals['error']:
            doc['dataset_scores'][dset]['error'] = vals['error']
        else:
            doc['dataset_scores'][dset]['score'] = vals['score']
        if prev_doc:
            prev_scores = prev_doc['dataset_scores'][dset]['score']
            prev_score = compute_dset_score(app.metrics[dset], prev_scores)
            overall_prev += prev_score * app.weight[dset]
            doc['dataset_scores'][dset]['prev_score'] = prev_scores
    doc['score'] = overall_score
    doc['prev_score'] = -math.inf
    if prev_doc:
        doc['prev_score'] = overall_prev
    return doc

def update_scores():
    """
    Refreshes the results page with the latest info from the db.
    """
    results = []
    for username in app.coll.find().distinct('username'):
        results.append(update_doc(username))
    results.sort(key=lambda r: r['score'], reverse=True)
    cur_rank, cur_score = 0, math.inf
    for cur_idx, doc in enumerate(results):
        if doc['score'] < cur_score:
            cur_rank = cur_idx + 1
            cur_score = doc['score']
        doc['rank'] = cur_rank
    return results

def calc_score(dataset, results, error):
    """
    Calculate accuracy and F1 for the given results list and dataset while
    checking for potential errors.
    """
    res = {'score': {metric['metric']: -math.inf for metric in
        app.metrics[dataset]}, 'error': error}
    if error:
        return res

    if len(results) != len(app.labels[dataset]):
        msg = "Got {} results, expected {}".format(len(results),
                len(app.labels[dataset]))
        res['error'] = msg
        return res

    matrix = metapy.classify.ConfusionMatrix()
    for predicted, actual in zip(results, app.labels[dataset]):
        matrix.add(predicted, actual, 1)

    for metric in app.metrics[dataset]:
        name = metric['metric']
        res['score'][name] = getattr(matrix, name)()
    return res

@app.route('/api', methods=['POST'])
def compute_metrics():
    """
    Takes lists of class labels for a student submission, calculates
    Accuracy and F1, and inserts the results into the database.
    """
    jdata = request.json
    token, alias, result_arr = jdata['token'], jdata['alias'], jdata['results']
    username = get_username(token)
    resp = {'submission_success': True}
    datasets = set(r['dataset'] for r in result_arr)
    scores, errors = {}, []
    if datasets != app.datasets:
        errors.append("Wrong datasets: {} vs {}".format(datasets, app.datasets))
        resp['submission_success'] = False
    elif username is None:
        errors.append('Failed to obtain username from GitLab')
        resp['submission_success'] = False
    else:
        for entry in result_arr:
            cur_dset = entry['dataset']
            score = calc_score(cur_dset, entry['results'], entry['error'])
            scores[cur_dset] = score
            if score['error']:
                errors.append("{}: {}".format(cur_dset, score['error']))
                resp['submission_success'] = False

    resp['error'] = '; '.join(errors) if len(errors) > 0 else None

    # only insert document if it's well formed
    if scores.keys() == app.datasets and username is not None:
        doc = {'username': username, 'alias': alias, 'dataset_scores': scores}
        app.coll.insert_one(doc)

    return Response(json.dumps(resp), status=200, mimetype='application/json')

@app.route('/')
def root():
    """
    Recalculates the latest scores and displays them.
    """
    return render_template('index.html', datasets=app.datasets,
                           metrics=app.metrics, weight=app.weight,
                           participants=update_scores(),
                           competition_name=app.competition_name)

def load_config(cfg_path):
    """
    Read the leaderboard config file, which specifies dataset-specific
    information.
    """
    app.labels, app.metrics, app.weight = {}, {}, {}
    app.datasets = set()
    with open(cfg_path) as infile:
        cfg = pytoml.load(infile)
    app.competition_name = cfg['competition-name']
    app.timezone = pytz.timezone(cfg['timezone'])
    app.gitlab_api_url = "{}/api/v3".format(cfg['gitlab-url'])
    for dset in cfg['datasets']:
        name = dset['name']
        app.weight[name] = dset['weight']
        app.metrics[name] = dset['metrics']
        with open(dset['label-file']) as infile:
            app.labels[name] = infile.read().splitlines()
        app.datasets.add(name)
    num = len(app.datasets)
    print("Loaded {} dataset{}: {}".format(num, '' if num == 1 else 's',
                                           app.datasets))

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python {} datasets.toml".format(sys.argv[0]))
        sys.exit(1)
    load_config(sys.argv[1])
    app.client = MongoClient(app.mongodb_host)
    app.coll = app.client['competition']['results']
    app.run(debug=True)
