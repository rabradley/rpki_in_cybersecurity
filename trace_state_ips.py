import tracer
import json
import os

if __name__ == "__main__":
	with open("./state_ips.json") as f:
		state_ips = json.load(f)

	for entry in state_ips:
		state, ips = entry
		print("TRACE_STATE_IPS:", state, len(ips))
		tracer.main(ip_list=ips, outfolder=f"./Outputs/USTraceroute/{state}")
