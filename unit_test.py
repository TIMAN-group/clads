import requests
import unittest
import metapy
import json
from timeout import Timeout
from search_eval import load_ranker

class TestRanker(unittest.TestCase):
    cfg_file = 'config.toml'
    submission_url = 'http://0.0.0.0:5000/api'
    top_k = 10
    queries = ['Airbus Subsidies', 'South African Sanctions',
               'Leveraged Buyouts', 'Satellite Launch Contracts',
               'Insider Trading']

    def test_creation(self):
        ranker = load_ranker()

    def test_load_index(self):
        idx = metapy.index.make_inverted_index(self.cfg_file)

    def test_upload_submission(self):
        """
        This is the unit test that actually submits the results to the
        leaderboard. If there is an error (on either end of the submission), the
        unit test is failed, and the failure string is also reproduced on the
        leaderboard.
        """
        req = {'netid': 'student22', 'alias': 'my_alias', 'results': None, 'error': None}
        timeout_len = 60
        try:
            with Timeout(timeout_len):
                ranker = load_ranker()
                idx = metapy.index.make_inverted_index(self.cfg_file)
                query = metapy.index.Document()
                results = []
                for query_text in self.queries:
                    query.content(query_text)
                    results.append(ranker.score(idx, query, self.top_k))
                req['results'] = results
        except Timeout.Timeout:
            error_msg = "Timeout error: {}s".format(timeout_len)
            req['error'] = error_msg
            print(error_msg)
        response = requests.post(self.submission_url, json=req)
        jdata = response.json()
        self.assertTrue(jdata['submission_success'])

if __name__ == '__main__':
    unittest.main()
