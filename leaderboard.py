from flask import Flask, request
app = Flask(__name__, static_folder='.', static_url_path='')
from pymongo import MongoClient

def write_html(ranked):
    cur_score = 1.1
    cur_rank = 0
    html = ''
    for result in ranked:
        if result['ndcg'] < cur_score:
            cur_rank += 1
        cur_score = result['ndcg']
        html += "<tr><td>{}</td><td>{}</td>".format(cur_rank, result['alias'])
        html += "<td>{}</td><td><em>{}</em></td></tr>\n".format(cur_score,
                result['previous'])
    return html

def get_scores(prune_old=True):
    """
    This assumes we have a MongoDB instance running with a db called
    "competition" and a collection called "results" with fields for alias and
    ndcg.
    """
    client = MongoClient()
    coll = client['competition']['results']
    results = []
    for netid in coll.find().distinct('netid'):
        docs = list(coll.find({'netid': netid}))
        docs.sort(key=lambda d: d['_id'].generation_time, reverse=True)
        doc = docs.pop(0)
        doc['previous'] = None
        if len(docs) > 0:
            prev = docs.pop(0)
            doc['previous'] = prev['ndcg']
        if prune_old and len(docs) > 0:
            for old in docs:
                coll.delete_one(old)
        results.append(doc)
    results.sort(key=lambda r: r['ndcg'], reverse=True)
    return write_html(results)

# TODO: can we have get_scores() called only on an update to the db?
@app.route('/')
def root():
    return "{}{}{}".format(app.head_html, get_scores(), app.tail_html)

if __name__ == '__main__':
    with open('index.html.head') as head_in:
        app.head_html = head_in.read()
    app.tail_html = '</table> </div> </div> </body> </html>'
    app.run(debug=True)
