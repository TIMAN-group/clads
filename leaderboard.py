import metapy
import json
from flask import Flask, request, Response
app = Flask(__name__, static_folder='.', static_url_path='')
from pymongo import MongoClient

def write_html(ranked):
    """
    Given the list of sorted results, display them in an HTML table.
    """
    cur_score = 1.1
    cur_rank = 0
    html = ''
    for result in ranked:
        if result['ndcg'] < cur_score:
            cur_rank += 1
        cur_score = result['ndcg']
        if cur_score == -1.0:
            cur_score = result['fail']
        html += "<tr><td>{}</td><td>{}</td>".format(cur_rank, result['alias'])
        html += "<td>{}</td><td><em>{}</em></td></tr>\n".format(cur_score,
                result['previous'])
    return html

def update_scores(prune_old=True):
    """
    Refreshes the results page with the latest info from the db. If prune_old is
    true, old scores are removed from the db.
    """
    results = []
    for netid in app.coll.find().distinct('netid'):
        docs = list(app.coll.find({'netid': netid}))
        docs.sort(key=lambda d: d['_id'].generation_time, reverse=True)
        doc = docs.pop(0)
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

def insert_results(netid, alias, results, fail_reason=None):
    """
    Score the student's submission and insert it if there wasn't a failure
    beforehand. If there was a failure, store the reason so it can be displayed
    on the leaderboard.
    """
    doc = {'netid': netid, 'alias': alias, 'ndcg': -1.0, 'fail': None}
    if fail_reason is None:
        ndcg = 0.0
        for query_num, result in enumerate(results):
            result = [tuple(elem) for elem in result]
            ndcg += app.ir_eval.ndcg(result, query_num, app.top_k)
        doc['ndcg'] = ndcg / app.num_queries
    else:
        doc['fail'] = fail_reason
    app.coll.insert_one(doc)

@app.route('/api', methods=['POST'])
def compute_ndcg():
    """
    Takes ranked lists of student submissions, calculates its NDCG, and inserts
    the results into the database.
    """
    jdata = request.json
    netid, alias, results = jdata['netid'], jdata['alias'], jdata['results']
    resp_data = {'submission_success': True}
    if len(results) != app.num_queries:
        insert_results(netid, alias, None,
                       fail_reason='Incorrect number of queries')
        resp_data['submission_success'] = False
    else:
        insert_results(netid, alias, results)
    return Response(json.dumps(resp_data), status=200,
                    mimetype='application/json')

# TODO: can we have update_scores() called only on an update to the db?
@app.route('/')
def root():
    """
    Recalculates the latest scores and displays them.
    """
    return "{}{}{}".format(app.head_html, update_scores(), app.tail_html)

if __name__ == '__main__':
    with open('index.html.head') as head_in:
        app.head_html = head_in.read()
    app.tail_html = '</table> </div> </div> </body> </html>'
    app.ir_eval = metapy.index.IREval('config.toml')
    app.top_k = 10
    app.num_queries = 5
    app.client = MongoClient()
    app.coll = app.client['competition']['results']
    app.run(debug=True)
