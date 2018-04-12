from pymongo import MongoClient
import random
import string

def random_alias():
    return ''.join(random.choice(string.ascii_lowercase) for _ in range(8))

if __name__ == '__main__':
    client = MongoClient()
    coll = client['competition']['results']
    usernames = ['bob', 'fred', 'billy', 'joe', 'sue', 'sally', 'ferdinand',
              'augustus', 'leonard']
    for username in usernames:
        alias = random_alias()
        ndcg = round(random.uniform(0, 1), 1)
        coll.insert({'username': username,
                     'alias': alias,
                     'dataset_scores': {'cranfield': {'score': ndcg, 'error': None}}
                    })
