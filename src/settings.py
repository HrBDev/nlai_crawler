import os

import pymongo
from dotenv import load_dotenv

load_dotenv()


def is_not_empty(string):
    return bool(string and string.strip())


conn_string = os.getenv('MONGODB_CONN_STRING')
db_name = os.getenv('DATABASE_NAME')
collection_name = os.getenv('COLLECTION_NAME')
target_collection = None
if is_not_empty(conn_string) and is_not_empty(db_name) and is_not_empty(collection_name):
    client = pymongo.MongoClient(os.getenv('MONGODB_CONN_STRING'))
    db = client[os.getenv('DATABASE_NAME')]
    target_collection = db[os.getenv('COLLECTION_NAME')]
