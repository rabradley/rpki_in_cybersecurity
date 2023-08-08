import tracer

import json
import math
import os
import shutil
import requests

PC_COUNT = 16
PC_INDEX = 0

"""

"""

with open("./upload.txt") as f:
	upload_url = f.read()

if __name__ == "__main__":
	with open("./state_ips.json") as f:
		state_ips = json.load(f)

	STATE_COUNT = len(state_ips)
	PER_GROUP = math.floor(STATE_COUNT / PC_COUNT)
	remainder = STATE_COUNT % PER_GROUP

	GROUPS = []
	for i in range(0, PC_COUNT):
		s = PER_GROUP * i
		group = [x for x in range(s, s + PER_GROUP)]
		GROUPS.append(group)

	last = GROUPS[len(GROUPS)-1]
	last += [x for x in range(last[len(last) - 1] + 1, last[len(last) - 1] + remainder + 1)]

	MY_GROUP = GROUPS[PC_INDEX]
	print(MY_GROUP)


	for idx, entry in enumerate(state_ips):
		if idx not in MY_GROUP:
			continue

		state, ips = entry
		if os.path.exists(f"C:/Users/Public/RPKI/{state}"):
			#print(f"State info for {state} already exists, skipping.")
			#continue
			pass

		print("TRACE_STATE_IPS:", state, len(ips))
		tracer.main(ip_list=ips, outfolder=f"C:/Users/Public/RPKI/{state}")

	shutil.make_archive(f"C:/Users/Public/RPKI_{PC_INDEX}", "zip", "C:/Users/Public/RPKI")
	r = requests.post(upload_url, files={
		"upload_file": open(f"C:/Users/Public/RPKI_{PC_INDEX}", "rb")
	})

