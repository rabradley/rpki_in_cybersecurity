import ipaddress
import logging
import json
import math
import os
import random
import re
import signal
import subprocess
import time
import traceback
import multiprocessing as mp

import pandas as pd

PING_RESULT = r"Reply from [\d.]+"
pattern = re.compile(PING_RESULT)

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Figured out how to do this by looking here: https://docs.python.org/3/library/logging.html#logging.basicConfig
#logging.basicConfig(format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.DEBUG)

# So I googled "set format for individual loggers python" and it took me to here: https://docs.python.org/3/howto/logging-cookbook.html#using-logging-in-multiple-modules

# To get milliseconds included: https://stackoverflow.com/a/7517430
formatter = logging.Formatter(fmt='%(asctime)s.%(msecs)03d %(message)s', datefmt='%m/%d/%Y %H:%M:%S')


console_handler = logging.StreamHandler()
console_handler.setLevel(logging.DEBUG)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)


# https://stackoverflow.com/questions/13733552/logger-configuration-to-log-to-file-and-print-to-stdout
file_handler = logging.FileHandler(os.path.splitext(os.path.split(__file__)[1])[0] + ".log", mode='w')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


the_queue = mp.Queue()

def get_prefixes_by_state():
	with open("./prefixes_by_state.json") as f:
		prefixes_by_state = json.load(f)

	return prefixes_by_state

"""
def get_ranges_by_state():
	logger.info("reading csv")
	df = pd.read_csv("IP2LOCATION-LITE-DB3.CSV", names=["start", "end", "country_code", "country", "state", "city"])

	logger.info("iterating")
	state_ranges = {}
	for idx, row in df.iterrows():
		state = row["state"]
		if state == "-" or state == "District of Columbia":
			continue

		if state not in state_ranges:
			state_ranges[state] = []

		state_ranges[state].append([
			row["start"], row["end"]
		])

	return state_ranges
"""

def ping_ip(ip):
	cmd = ["ping", "-w", "500", "-n", "2", ip]
	cmd = " ".join(cmd)

	result = os.popen(cmd).read()
	matches = re.findall(r"Reply from [\d.]+", result)

	return len(matches) > 0


def get_ips_by_state(state, how_many, prefixes):
	state_ips = []

	logger.info(f"get_ips_by_state({state})")

	all_hosts = []
	for i, prefix in enumerate(prefixes):
		network = ipaddress.ip_network(prefix)
		all_hosts += [str(host) for host in network.hosts() if random.randint(1, 10) <= 1]

	logger.info(f"begin {state} ({len(all_hosts)})")

	while len(state_ips) < how_many:
		idx = random.randint(0, len(all_hosts) - 1)
		ip = all_hosts.pop(idx)

		if ping_ip(ip):
			state_ips.append(ip)

	logger.info(f"Finished state: {state}")

	return state_ips



def worker_main(stuff):
	#logger.info(os.getpid(), "working")
	state, how_many, prefixes = stuff

	save_path = f"./valid_ips/{state}.json"
	with open(save_path, "w") as f:
		f.write("in progress")

	ips = get_ips_by_state(state, how_many, prefixes)

	with open(save_path, "w") as f:
		json.dump(ips, f)

	return state, ips

def mp_get_random_ips(how_many):
	os.makedirs(f"./valid_ips", exist_ok=True)
	state_prefixes = get_prefixes_by_state()

	logger.info("done collecting")

	tasks = [[state, how_many, data] for state, data in state_prefixes.items() if state != "-" and state != "District of Columbia"]

	logger.info("done queueing")

	def sigint_handler(signal, frame):
		logger.error("Received interrupt signal, exiting. " + "=" * 50)
		pool.terminate()
		exit(1)

	signal.signal(signal.SIGINT, sigint_handler)

	def error_callback(e):
		logger.error("callback error")
		traceback.print_exception(type(e), e, e.__traceback__)
		pool.terminate()
		logger.error("Worker pool has consequently been terminated, exiting.")

	# exit(1)

	logger.info("pool startup")

	with mp.Pool(processes=12) as pool:
		# See comments in RPKI project for reasoning on why this is done like this
		results = pool.map_async(worker_main, iterable=tasks, error_callback=error_callback)
		while True:
			time.sleep(0.5)
			try:
				# These need to be done here to get the exception.
				ready = [results.ready()]
				successful = [results.successful()]
			except Exception as err:
				if pool._state == "TERMINATE":
					break
				continue

			if all(successful):
				# Everything completed successfully.
				successful_run = True
				break
			elif all(ready):
				# Not everything completed successfully, but everything is ready now.
				raise Exception("get valid ip failed")

	if successful_run:
		# Everything processed successfully.
		logger.info("get valid ip finished")
		return results.get()
	else:
		logger.error("Error in pool processing")
		exit(1)

def main():
	how_many = 100
	res = mp_get_random_ips(how_many)

	with open("./state_ips.json", "w") as f:
		json.dump(res, f)


if __name__ == "__main__":
	main()

