import json, sys
json.dump({"builds": 0}, open(sys.argv[1], "w"))
