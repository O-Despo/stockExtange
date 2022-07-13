from pymongo import MongoClient
import json

FILE_TO_INSERT = "./bsuser.json"

client = MongoClient("localhost:27017")
db = client["stonky_beta_1"]
col = db["users"]

with open(FILE_TO_INSERT, "r") as file:
    bddata = json.load(file)
    print(type(bddata))
    if type(bddata) == list:
        data = bddata[0]
    data["discord_id"] = data["discord_id"]["$numberLong"]

    del data["_id"]
    outcome = col.insert_one(data)

print(outcome)

