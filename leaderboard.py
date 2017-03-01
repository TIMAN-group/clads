import sys
import json
import metapy
import requests
import pytoml

from flask import Flask, request, Response
app = Flask(__name__, static_folder='.', static_url_path='')
from pymongo import MongoClient

GITLAB_API_URL = 'https://gitlab.textdata.org/api/v3'

def get_netid(token):
    try:
        r = requests.get("{}/user".format(GITLAB_API_URL),
                         headers={'PRIVATE-TOKEN': token})
        return r.json()['username']
    except:
        return None

def make_tr(elems):
    def td_elem(elem):
        return "<td>{}</td>".format(elem)
    return "<tr>{}</tr>\n".format(''.join([td_elem(e) for e in elems]))

def write_html(ranked):
    """
    Given the list of sorted results, display them in an HTML table.
    """
    cur_score = 1.1
    cur_rank = 0
    html = ''
    error_glyph = '<span class="glyphicon glyphicon-warning-sign"';
    error_glyph += 'aria-hidden="true" title="An error occurred!"></span>'
    for cur_idx, result in enumerate(ranked):
        if result['ndcg'] < cur_score:
            cur_rank = cur_idx + 1
        cur_score = result['ndcg']
        if cur_score == -1.0:
            display_score = "{}&nbsp;{}".format(error_glyph, result['error'])
        else:
            display_score = "{:8.5f}".format(cur_score)
        if result['previous'] == -1.0:
            display_prev = error_glyph
        else:
            display_prev = "{:8.5f}".format(result['previous'])
        gen_time = result['_id'].generation_time.strftime('%Y-%m-%d | %H:%M:%S')
        html += make_tr([cur_rank, result['alias'], display_score,
                         display_prev, gen_time, result['submissions']])
    return html

def update_scores(prune_old=False):
    """
    Refreshes the results page with the latest info from the db. If prune_old is
    true, old scores are removed from the db.
    """
    results = []
    for netid in app.coll.find().distinct('netid'):
        docs = list(app.coll.find({'netid': netid}))
        docs.sort(key=lambda d: d['_id'].generation_time, reverse=True)
        doc = docs.pop(0)
        doc['submissions'] = len(docs) + 1
        doc['previous'] = None
        if len(docs) > 0:
            prev = docs.pop(0)
            doc['previous'] = prev['ndcg']
        if prune_old and len(docs) > 0:
            for old in docs:
                app.coll.delete_one(old)
        results.append(doc)
    results.sort(key=lambda r: r['ndcg'], reverse=True)
    return write_html(results)

def insert_results(netid, alias, dataset, results, error):
    """
    Score the student's submission and insert it if there wasn't a failure
    beforehand. If there was a failure, store the reason so it can be displayed
    on the leaderboard.
    """
    doc = {'netid': netid, 'dataset': dataset, 'alias': alias, 'ndcg': -1.0,
           'error': None}
    retval = True
    if results is None or error is not None:
        doc['error'] = error
        doc['results'] = None
        retval = False
    elif len(results) != app.num_queries[dataset]:
        msg = "Got {} queries, expected {}".format(len(results),
                                                   app.num_queries[dataset])
        doc['error'] = msg
        doc['results'] = None
        retval = False
    else:
        ndcg = 0.0
        query_start = app.query_start[dataset]
        for query_num, result in enumerate(results):
            result = [tuple(elem) for elem in result]
            ndcg += app.ir_eval[dataset].ndcg(result, query_num + query_start,
                                              app.top_k[dataset])
        doc['ndcg'] = ndcg / app.num_queries[dataset]
    app.coll.insert_one(doc)
    return retval

@app.route('/api', methods=['POST'])
def compute_ndcg():
    """
    Takes ranked lists of student submissions, calculates its NDCG, and inserts
    the results into the database.
    """
    jdata = request.json
    token, alias, result_arr = jdata['token'], jdata['alias'], jdata['results']
    netid = get_netid(token)
    resp = {'submission_success': True}
    datasets = set(r['dataset'] for r in result_arr)
    errors = []
    if datasets != app.datasets:
        errors.append("Mismatched datasets: {} vs {}".format(datasets,
                                                             app.datasets))
        resp['submission_success'] = False
    elif netid is None:
        resp['submission_success'] = False
        errors.append('Failed to obtain netid from GitLab')
    else:
        for entry in result_arr:
            success = insert_results(netid, alias, entry['dataset'],
                                     entry['results'], entry['error'])
            if not success:
                errors.append("{}: {}".format(entry['dataset'], entry['error']))
                resp['submission_success'] = False
    resp['error'] = '; '.join(errors) if len(errors) > 0 else None
    return Response(json.dumps(resp), status=200, mimetype='application/json')

@app.route('/')
def root():
    """
    Recalculates the latest scores and displays them.
    """
    return "{}{}{}".format(app.head_html, update_scores(), app.tail_html)

def load_config():
    """
    Read the leaderboard config file, which specifies dataset-specific
    information.
    """
    app.ir_eval, app.top_k, app.num_queries, app.query_start = {}, {}, {}, {}
    app.datasets = set()
    with open(sys.argv[1]) as infile:
        cfg = pytoml.load(infile)
    for dset in cfg['datasets']:
        name = dset['name']
        app.ir_eval[name] = metapy.index.IREval(dset['config'])
        app.top_k[name] = dset['top-k']
        app.num_queries[name] = dset['num-queries']
        app.query_start[name] = dset['query-id-start']
        app.datasets.add(name)
    num = len(app.datasets)
    print("Loaded {} dataset{}: {}".format(num, '' if num == 1 else 's',
                                           app.datasets))

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python {} datasets.toml".format(sys.argv[0]))
        sys.exit(1)
    with open('index.html.head') as head_in:
        app.head_html = head_in.read()
    app.tail_html = '</table> </div> </div> </body> </html>'
    load_config()
    app.client = MongoClient()
    app.coll = app.client['competition']['results']
    app.run(debug=True)
