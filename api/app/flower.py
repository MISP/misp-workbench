import os
import requests

# create requests session with basic auth 

user = os.environ.get("FLOWER_BASIC_AUTH").split(":")[0]
password = os.environ.get("FLOWER_BASIC_AUTH").split(":")[1]

FlowerClient = requests.Session()
FlowerClient.auth = (user, password)
