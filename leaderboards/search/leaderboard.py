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
        overall_score += vals['score'] * app.weight[dset]
        doc['dataset_scores'][dset]['prev_score'] = -math.inf
        # If there was an error, show error text instead of -inf score.
        if vals['error']:
            doc['dataset_scores'][dset]['error'] = vals['error']
        else:
            doc['dataset_scores'][dset]['score'] = vals['score']
        if prev_doc:
            prev_score = prev_doc['dataset_scores'][dset]['score']
            overall_prev += prev_score * app.weight[dset]
            doc['dataset_scores'][dset]['prev_score'] = prev_score
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
    Calculate IR eval score for the given results list and dataset while
    checking for potential errors.
    """
    res = {'score': -math.inf, 'error': error}
    if error:
        return res
    num_queries = app.num_queries[dataset]
    if len(results) != num_queries:
        msg = "Got {} queries, expected {}".format(len(results), num_queries)
        res['error'] = msg
        return res
    ndcg = 0.0
    query_start = app.query_start[dataset]
    for query_num, result in enumerate(results):
        result = [tuple(elem) for elem in result]
        ndcg += app.ir_eval[dataset].ndcg(result, query_num + query_start,
                                          app.top_k[dataset])
    res['score'] = ndcg / app.num_queries[dataset]
    return res

@app.route('/api', methods=['POST'])
def compute_ndcg():
    """
    Takes ranked lists of student submissions, calculates its NDCG, and inserts
    the results into the database.
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
                           top_k=app.top_k, weight=app.weight,
                           participants=update_scores(),
                           competition_name=app.competition_name)

def load_config(cfg_path):
    """
    Read the leaderboard config file, which specifies dataset-specific
    information.
    """
    app.ir_eval, app.top_k, app.num_queries, app.query_start, app.weight = {}, {}, {}, {}, {}
    app.datasets = set()
    with open(cfg_path) as infile:
        cfg = pytoml.load(infile)
    app.competition_name = cfg['competition-name']
    app.timezone = pytz.timezone(cfg['timezone'])
    app.mongodb_host = cfg['mongodb-host']
    app.gitlab_api_url = "{}/api/v3".format(cfg['gitlab-url'])
    for dset in cfg['datasets']:
        name = dset['name']
        app.ir_eval[name] = metapy.index.IREval(dset['config'])
        app.top_k[name] = dset['top-k']
        app.num_queries[name] = dset['num-queries']
        app.query_start[name] = dset['query-id-start']
        app.weight[name] = dset['weight']
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
