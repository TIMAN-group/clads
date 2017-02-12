from pymongo import MongoClient

def add_scores():
    """
    Loop through entries in DB and select the latest ones for each unique user
    id. Sort in descending order and display in table rows. Can also add a
    column for "previous score" and "best score" etc.

    This assumes we have a MongoDB instance running with a db called
    "competition" and a collection called "results" with fields for alias and
    ndcg.

    These docs are inserted into the DB while running unit_test.py. Each
    student's ranking function should have an alias member variable, and we need
    a way to get a user id (grading script should have this).
    """
    client = MongoClient()
    coll = client['competition']['results']
    html = ''
    for idx, result in enumerate(coll.find()):
        html += "<tr><td>{}</td><td>{}</td>".format(idx + 1, result['alias'])
        html += "<td>{}</td></tr>\n".format(result['ndcg'])
    return html

if __name__ == '__main__':
    with open('index.html.head') as head_in:
        html = head_in.read()
    html += add_scores()
    with open('index.html', 'w') as outfile:
        outfile.write(html)
        outfile.write('</table> </div> </div> </body> </html>')
