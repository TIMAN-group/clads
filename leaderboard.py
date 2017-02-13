from flask import Flask, request
app = Flask(__name__, static_folder='.', static_url_path='')
from pymongo import MongoClient

def get_scores():
    """
    Loop through entries in DB and select the latest ones for each unique user
    id. Sort in descending order and display in table rows. Can also add a
    column for "previous score" and "best score" etc.

    This assumes we have a MongoDB instance running with a db called
    "competition" and a collection called "results" with fields for alias and
    ndcg.
    """
    client = MongoClient()
    coll = client['competition']['results']
    html = ''
    for idx, result in enumerate(coll.find()):
        html += "<tr><td>{}</td><td>{}</td>".format(idx + 1, result['alias'])
        html += "<td>{}</td></tr>\n".format(result['ndcg'])
    return html

@app.route('/')
def root():
    return "{}{}{}".format(app.head_html, get_scores(), app.tail_html)

if __name__ == '__main__':
    with open('index.html.head') as head_in:
        app.head_html = head_in.read()
    app.tail_html = '</table> </div> </div> </body> </html>'
    app.run(debug=True)
