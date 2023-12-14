from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route("/health")
def check_health():
    return {"status": "OK"}, 200

@app.route("/count")
def count():
    #Find all songs from the songs collection, and cast it into a list
    song_list = list(db.songs.find())
    return {"count": len(song_list)}

@app.route("/song")
def songs():
    song_list = list(db.songs.find())
    return {"songs": parse_json(song_list)}

@app.route("/song/<int:id>")
def get_song_by_id(id):
    found_song = db.songs.find_one({"id": id})
    if not found_song:
       return {"message": "song with id not found"}, 404
    return parse_json(found_song)

@app.route("/song", methods=["POST"])
def create_song():
    song_data = request.json

    song = db.songs.find_one({"id": song_data["id"]})
    if song:
        return {"Message": f"song with id {song_data['id']} already present"}, 302
    db.songs.insert_one(song_data)
    song_oid = parse_json(db.songs.find_one({"id": song_data["id"]}, {"_id": 1}))
    return {"inserted id": song_oid["_id"]}, 201

@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    song_data = request.json
    find_song = db.songs.find_one({"id": id})
    if not find_song:
        return {"message": "song not found"}, 404
 
    result = db.songs.update_one({"id": id}, {"$set": song_data})
    if result.modified_count == 0:
        return {"message": "song found, but nothing updated"}
    return parse_json(db.songs.find_one({"id": id})), 201

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    result = db.songs.delete_one({"id": id})
    if result.deleted_count == 0:
        return {"message": "song not found"}, 404
    return "", 204