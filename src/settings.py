import os

import pymongo
from dotenv import load_dotenv

load_dotenv()

client = pymongo.MongoClient(os.getenv('MONGODB_CONN_STRING'))
db = client[os.getenv('DATABASE_NAME')]
mycol = db[os.getenv('COLLECTION_NAME')]
