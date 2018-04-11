import math
import sys
import time

import metapy
import pytoml

def load_ranker(cfg_file):
    """
    Use this function to return the Ranker object to evaluate.

    The parameter to this function, cfg_file, is the path to a
    configuration file used to load the index. You can ignore this, unless
    you need to load a ForwardIndex for some reason...
    """
    return metapy.index.JelinekMercer()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: {} config.toml".format(sys.argv[0]))
        sys.exit(1)

    cfg = sys.argv[1]
    print('Building or loading index...')
    idx = metapy.index.make_inverted_index(cfg)
    ranker = load_ranker(cfg)
    ev = metapy.index.IREval(cfg)

    with open(cfg, 'r') as fin:
        cfg_d = pytoml.load(fin)

    query_cfg = cfg_d['query-runner']
    if query_cfg is None:
        print("query-runner table needed in {}".format(cfg))
        sys.exit(1)

    start_time = time.time()
    top_k = 10
    query_path = query_cfg.get('query-path', 'queries.txt')
    query_start = query_cfg.get('query-id-start', 0)

    query = metapy.index.Document()
    print('Running queries')
    ndcg = []
    with open(query_path) as query_file:
        for query_num, line in enumerate(query_file):
            query.content(line.strip())
            results = ranker.score(idx, query, top_k)
            avg_p = ev.avg_p(results, query_start + query_num, top_k)
            ndcg.append(ev.ndcg(results, query_start + query_num, top_k))
            print("Query {} average precision: {}".format(query_num + 1, avg_p))
    print("Mean average precision: {}".format(ev.map()))
    print("Avg NDCG@10: {}".format(sum(ndcg) / len(ndcg)))
    print("Elapsed: {} seconds".format(round(time.time() - start_time, 4)))
