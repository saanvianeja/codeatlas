import json
import os


def dump(data):
    return json.dumps(data) + os.sep
