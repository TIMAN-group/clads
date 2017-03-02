import json
import metapy
import os
import pytoml
import requests
import unittest
from tqdm import *
from timeout import Timeout
from search_eval import load_ranker


class TestRanker(unittest.TestCase):
    cfgs = [
        # Cranfield
        '/data/cranfield/config.toml',
        # APNews
        '/data/apnews/config.toml'
    ]
    submission_url = 'http://0.0.0.0:5000/api'
    top_k = 10

    def test_creation(self):
        for cfg_file in self.cfgs:
            ranker = load_ranker(cfg_file)

    def test_load_index(self):
        for cfg_file in self.cfgs:
            idx = metapy.index.make_inverted_index(cfg_file)

    def get_results(self, cfg_file, query_path):
        ranker = load_ranker(cfg_file)
        idx = metapy.index.make_inverted_index(cfg_file)
        query = metapy.index.Document()

        results = []
        with open(query_path, 'r') as query_file:
            queries = query_file.readlines()

        for line in tqdm(queries):
            query.content(line.strip())
            results.append(ranker.score(idx, query, self.top_k))
        return results

    def test_upload_submission(self):
        """
        This is the unit test that actually submits the results to the
        leaderboard. If there is an error (on either end of the submission),
        the unit test is failed, and the failure string is also reproduced
        on the leaderboard.
        """
        req = {
            'token': os.environ.get('GITLAB_API_TOKEN'),
            'alias': os.environ.get('COMPETITION_ALIAS') or 'Anonymous',
            'results': []
        }

        for cfg_file in self.cfgs:
            res = {'error': None}
            with open(cfg_file, 'r') as fin:
                cfg_d = pytoml.load(fin)
            res['dataset'] = cfg_d['dataset']
            print("\nRunning on {}...".format(res['dataset']))
            query_path = cfg_d['query-runner']['query-path']
            timeout_len = cfg_d['query-runner']['timeout']

            try:
                with Timeout(timeout_len):
                    res['results'] = self.get_results(cfg_file, query_path)
            except Timeout.Timeout:
                error_msg = "Timeout error: {}s".format(timeout_len)
                res['error'] = error_msg
                res['results'] = []

            req['results'].append(res)

        response = requests.post(self.submission_url, json=req)
        jdata = response.json()
        print(jdata)
        self.assertTrue(jdata['submission_success'])


if __name__ == '__main__':
    unittest.main()
