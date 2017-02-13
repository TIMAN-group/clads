from pymongo import MongoClient
import random
import string

def random_netid():
    return "{}{}".format(random_alias(), random.choice([range(100)]))

def random_alias():
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(8))

if __name__ == '__main__':
    client = MongoClient()
    coll = client['competition']['results']
    netids = ['bob', 'fred', 'billy', 'joe', 'sue', 'sally', 'ferdinand',
              'augustus', 'leonard']
    for netid in netids:
        alias = random_alias()
        ndcg = round(random.uniform(0, 1), 1)
        coll.insert({'netid': netid, 'alias': alias, 'ndcg': ndcg})
