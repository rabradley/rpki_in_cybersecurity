#######################################################
# Imports #############################################
#######################################################


import argparse
import datetime
import json
import logging
import os
import pandas as pd
import multiprocessing as mp
import re
import signal
import socket
import sys
import time
import traceback
import typing
from urllib.parse import urlparse

import requests

# import scapy.layers.inet as scapyinet

#######################################################
# Globals #############################################
#######################################################
RIPE_RPKI = "https://stat.ripe.net/data/rpki-validation/data.json?resource={}&prefix={}"

WIN32_TRACE = ["tracert", "-d"]
# WIN32_TRACE_PATTERN = r"\s+(\d+)\s+([<\d\w\s]+)\s+(\d+\.\d+\.\d+\.\d+)"  # /g # Doesn't account for timeouts
WIN32_TRACE_PATTERN = r"^\s*(\d+)\s+([<\d\sms*]+)\s+([\w\d\s.]+)\s*$"  # /gm
# WIN32_TRACE_DEST_IP = r"Tracing route to [\w\d.-]+ \[(\d+\.\d+\.\d+\.\d+)\]"
WIN32_TRACE_DEST_IP = r"Tracing route to ([\w\d.-]+)[\s\w]*\[*([\d.]*)\]*"

"""
Tracing route to 93.184.216.34 over a maximum of 30 hops
                                                        
  1    <1 ms    <1 ms    <1 ms  10.0.0.1                
  2     2 ms     1 ms     1 ms  10.255.235.4 
  3     3 ms     1 ms     2 ms  216.169.31.34 
  4     1 ms     1 ms     1 ms  216.169.31.8 
  5     6 ms     6 ms     5 ms  168.143.228.224 
  6    32 ms    18 ms     6 ms  129.250.196.166 
  7     6 ms     6 ms     6 ms  192.229.227.129 
  8     6 ms     6 ms     6 ms  93.184.216.34 

"""

"""
Tracing route to REDACTED.com [25.25.25.25]
over a maximum of 30 hops:

  1    <1 ms    <1 ms    <1 ms  10.0.0.1
  2     2 ms     2 ms     2 ms  10.255.235.4 
  3     2 ms     2 ms     2 ms  216.169.31.80 
  4     1 ms     1 ms     1 ms  216.169.31.10 
  5    19 ms    19 ms     6 ms  168.143.228.224 
  6     6 ms     7 ms    11 ms  129.250.2.23 
  7    27 ms    26 ms    29 ms  129.250.2.167 
  8    27 ms    26 ms    26 ms  129.250.3.128 
  9    38 ms    29 ms    34 ms  157.238.179.154 
 10     *        *        *     Request timed out.
 11     *        *        *     Request timed out.
 12     *        *        *     Request timed out.
 13     *        *        *     Request timed out.
 14    32 ms    31 ms    31 ms  25.25.25.25
"""

# AS | IP | BGP Prefix | CC | Registry | Allocated | Info | AS Name

# This one doesn't match for IPs like 10.0.0.1, which makes sense.
# CYMRU_PATTERN = r"^([\w\d]+)\s*\|\s*([\d.]+)\s*\|\s*([\d\w./]+)\s*\|\s*(\w+)\s*\|\s*(\w+)\s*\|\s*([\w\d-]+)\s*\|\s*(.+)$"
# This one matches everything though.
CYMRU_PATTERN = r"^([\w\d]+)\s*\|\s*([\d.]+)\s*\|\s*([\d\w./]+)\s*\|\s*(\w*)\s*\|\s*(\w+)\s*\|\s*([\w\d-]*)\s*\|\s*(.+)$"

# This pattern will not match the NA lines because the country doesn't have anything populated and thus breaks the pattern.
"""
Bulk mode; whois.cymru.com [2023-07-19 04:06:45 +0000]
NA      | 10.0.0.1         | NA                  |    | other    |            | NA
NA      | 10.255.235.4     | NA                  |    | other    |            | NA
12119   | 216.169.31.34    | 216.169.30.0/23     | US | arin     | 2017-06-27 | I3BROADBAND, US
12119   | 216.169.31.8     | 216.169.30.0/23     | US | arin     | 2017-06-27 | I3BROADBAND, US
2914    | 168.143.228.224  | 168.143.0.0/16      | US | arin     | 1994-05-13 | NTT-LTD-2914, US
2914    | 129.250.196.166  | 129.250.0.0/16      | US | arin     | 1988-04-05 | NTT-LTD-2914, US
15133   | 192.229.227.129  | 192.229.227.0/24    | US | arin     | 2013-02-07 | EDGECAST, US
15133   | 93.184.216.34    | 93.184.216.0/24     | US | ripencc  | 2008-06-02 | EDGECAST, US

"""

PROCESS_START_TIME = time.time()

#######################################################
# Classes #############################################
#######################################################
class ASMapping(typing.TypedDict):
	asn: str
	ip: str
	prefix: str

class Hop(typing.TypedDict):
	# hop: int
	timestr: str
	ip: str

class TracerouteResult(typing.TypedDict):
	output: list[Hop]
	destination_ip: str
	completed: bool

class HelpParser(argparse.ArgumentParser):
	def error(self, message):
		sys.stderr.write("Error: %s\n" % message)
		self.print_help()
		sys.exit(2)



#######################################################
# Functions ###########################################
#######################################################
def get_IPs_from_file(infile: str, column: str = None) -> list[str]:
	ext = os.path.splitext(infile)[1]

	if ext == ".txt":
		with open(args.infile, "r") as f:
			return list(map(lambda l: l.strip(), f.readlines()))
	elif ext == ".csv":
		if column is None:
			logger.error("Unable to process .csv without specifying the column to get URLs from.")
			exit(1)

		df = pd.read_csv(infile)
		sites = df[column]
		return list(sites.apply(lambda x: urlparse(x).netloc))
	else:
		logger.error(f"Unable to process infile of filetype [{ext}]")
		exit(1)

def create_latex_table(columns: list, data: list, caption: str, label: str, hlines: bool = True) -> str:
	c_str = "|" + "c|" * len(columns)
	columns_str = " & ".join(columns)
	data_str = []

	hline_sep = (hlines and "\n\t\t\\hline\n\t\t") or "\n\t\t"

	for row in data:
		# Todo: Let columns be chosen if type is a dict
		if type(row) == list:
			data_str.append(" & ".join(str(v) for v in row) + "\\\\")
		elif type(row) == str:
			x = "\\multicolumn{" + str(len(columns)) + "}{|c|}{" + row + "}"
			data_str.append(x + "\\\\")

	data_str = hline_sep.join(data_str)

	tex = """\\begin{table}[H]
	\\centering
	\\begin{tabular}{""" + c_str + """}
		\\hline
		""" + columns_str + """ \\\\
		\\hline
		""" + data_str + """
		\\hline
	\\end{tabular}
	\\caption{""" + caption + """}
	\\label{""" + label + """}
\\end{table}"""

	return tex


def get_rpki_data(asn: str, ip_prefix: str):
	res = requests.get(RIPE_RPKI.format(asn, ip_prefix))
	# Who needs error handling?
	res = res.json()

	"""
	{
		"messages": [],
		"see_also": [],
		"version": "0.3",
		"data_call_name": "rpki-validation",
		"data_call_status": "supported",
		"cached": false,
		"data": {
			"validating_roas": [
				{
					"origin": "2914",
					"prefix": "129.250.0.0/16",
					"max_length": 16,
					"validity": "valid"
				}
			],
			"status": "valid",
			"validator": "routinator",
			"resource": "2914",
			"prefix": "129.250.0.0/16"
		},
		"query_id": "20230719055023-50f20c0c-9213-4d5f-9f83-0427b6179744",
		"process_time": 28,
		"server_id": "app125",
		"build_version": "live.2023.7.18.163",
		"status": "ok",
		"status_code": 200,
		"time": "2023-07-19T05:50:23.900530"
	}
	"""

	return res["data"]

def mapToASes(ips: list[str]) -> dict[str, ASMapping]:
	"""
	Maps a list of IPs to their autonomous systems.

	:param ips:
	:return:
	"""
	# https://docs.python.org/3/library/socket.html
	# https://docs.python.org/3/howto/sockets.html

	# 15169   | 8.8.8.8          | 8.8.8.0/24          | US | arin     | 1992-12-01 | GOOGLE, US

	s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	s.connect(("whois.cymru.com", 43))
	s.send(b"begin\n")
	s.send(b"verbose\n")

	results = str(s.recv(256), "ascii")
	for idx, ip in enumerate(ips):
		s.send(bytes(ip + "\n", "ascii"))
		res = s.recv(256)
		results += str(res, "ascii")

	s.send(b"end\n")
	s.close()

	"""
	results = ""
	while True:
		msg = s.recv(2^5)
		if msg == b'':
			break
		results += str(msg, "ascii")
	"""

	#with open("afgh.txt", "w") as f:
		#f.write("\n".join(ips))

	#with open("asd.txt", "w") as f:
		#f.write(results)

	lines = results.splitlines()
	lines.pop(0)
	data = {}

	pattern = re.compile(CYMRU_PATTERN)

	for line in lines:
		match = pattern.match(line)

		# Two notable differences between a private and something without an AS: CC and Allocated
		# NA      | 10.10.9.29       | NA                  |    | other    |            | NA
		# NA      | 198.28.137.80    | NA                  | US | arin     | 2019-07-01 | NA

		if match:
			AS, IP, BGP_Prefix, CC, Registry, Allocated, AS_Name = match.groups()

			data[IP] = {
				"asn": AS,
				"ip": IP,
				"prefix": BGP_Prefix
			}
		else:
			raise Exception('oh no!')

	#with open("data.json", "w") as f:
		#json.dump(data, f, indent="\t")

	return data

def parse_output(results: str) -> (list[Hop], str):
	hop_pattern = re.compile(WIN32_TRACE_PATTERN)

	route_data = []

	lines = results.splitlines()

	"""
	Tracing route to google.com [142.250.191.238]
	Tracing route to 8.8.8.8 over a maximum of 30 hops
	"""

	destination_ip = re.match(WIN32_TRACE_DEST_IP, lines[1])
	if destination_ip.group(2) == "":
		destination_ip = destination_ip.group(1)
	else:
		destination_ip = destination_ip.group(2)

	#logger.info(lines[1])
	#logger.info(destination_ip)

	for line in lines:
		line = line.strip()
		match = hop_pattern.match(line)
		if match:
			hop, _time, ip = match.groups()

			h: Hop = {"timestr": _time, "ip": ip}
			if _time.find("*") == -1:
				route_data.append(h)

	return route_data, destination_ip

def traceroute(addresses: list[str] | str) -> list[TracerouteResult]:
	# res, unanswered = traceroute(ipaddr, maxttl=32)

	if type(addresses) == str:
		addresses = [addresses]

	results = []
	for addr in addresses:
		cmd = " ".join(WIN32_TRACE + [addr])
		logger.info(f"Performing traceroute for \"{addr}\" via [{cmd}]")
		trace = os.popen(cmd).read()

		output, dest_ip = parse_output(trace)
		completed = output[len(output)-1]["ip"] == dest_ip

		r: TracerouteResult = {"output": output, "destination_ip": dest_ip, "completed": completed}

		results.append(r)

	return results

def mp_traceroute(addresses: list[str] | str) -> list[TracerouteResult]:
	process_count = min(len(addresses), mp.cpu_count())

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

	successful_run = False
	with mp.Pool(processes=process_count) as pool:
		# See comments in RPKI project for reasoning on why this is done like this
		results = [pool.apply_async(traceroute, args=(addr,), error_callback=error_callback) for addr in addresses]
		last_ready = 0
		while True:
			time.sleep(0.5)
			try:
				# These need to be done here to get the exception.
				ready = [r.ready() for r in results]
				last_ready = ready.count(True)
				successful = [r.successful() for r in results]
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
				raise Exception("MP Traceroute failed")

	if successful_run:
		# Everything processed successfully.
		logger.info("MP Traceroute finished")
		return [r.get()[0] for r in results]
	else:
		logger.error("Error in pool processing")
		exit(1)


def main(ip_list: list[str], outfolder: str = None, multiprocessing: bool = True) -> list[list]:
	trace_start = time.time()
	if multiprocessing:
		logger.info("Using multiprocessing for traceroutes.")
		traces = mp_traceroute(ip_list)
	else:
		logger.info("Multiprocessing disabled, using single process.")
		traces = traceroute(ip_list)

	trace_end = time.time()

	logger.info(f"Finished tracing IPs, time elapsed: {datetime.timedelta(seconds=trace_end-trace_start)}")

	if outfolder and outfolder.lower() == os.devnull:
		logger.info("Outfolder is going to null device.")
		outfolder = None

	if outfolder and not os.path.exists(outfolder):
		os.makedirs(outfolder, exist_ok=True)

	summary = None
	if outfolder:
		summary = pd.DataFrame(columns=["destination", "destination_ip", "num_unique_prefixes", "num_valid", "num_invalid", "num_notfound", "hops", "completed"], dtype=str)

	# Collect every hop IP we've worked with for a bulk query
	logger.debug("Combining hop list")
	all_hop_ips = []
	for index, trace_data in enumerate(traces):
		hop_list = trace_data["output"]
		all_hop_ips += list(map(lambda x: x["ip"], hop_list))

	# Remove duplicates
	all_hop_ips = list(set(all_hop_ips))

	logger.info(f"Mapping hops ({len(all_hop_ips)}) to ASes")
	# Perform bulk query
	all_as_mappings = mapToASes(all_hop_ips)

	logger.info("Beginning calculations")
	all_raw_data = []
	for index, trace_data in enumerate(traces):
		hop_list = trace_data["output"]
		target_ip = ip_list[index]

		unique_prefixes = []
		num_valid = 0
		num_invalid = 0
		num_notfound = 0

		raw_data = []
		for hop_number, hop in enumerate(hop_list):
			# logger.debug(hop["ip"], hop_number, hop)
			ip = hop["ip"]
			as_data = all_as_mappings[ip]
			# logger.debug(f"\tGetting RPKI Data for {as_data['asn']}, {as_data['prefix']}")
			rpki_data = get_rpki_data(as_data["asn"], as_data["prefix"])

			unique = True
			if (as_data["prefix"] is None or as_data["prefix"] == "NA") or (as_data["prefix"] in unique_prefixes):
				unique = False
			else:
				unique_prefixes.append(as_data["prefix"])


			asn = as_data["asn"] or "-"
			prefix = as_data["prefix"] or "-"
			status = "-"

			if "status" in rpki_data:
				status = rpki_data["status"]

				if unique:
					if status == "valid":
						num_valid += 1
					elif status.find("invalid") != -1:
						logger.warning(f"Invalid Type: {status}")
						num_invalid += 1
					elif status == "unknown":
						num_notfound += 1
					else:
						logger.debug(ip)
						logger.debug(asn)
						logger.debug(status)
						logger.debug('=' * 50)
						logger.debug(hop)
						logger.debug(as_data)
						logger.debug(rpki_data)
						raise Exception("unknown status")

			# df.concat({"hop": key, "ip": ip, "prefix": prefix, "asn": asn, "status": status})
			raw_data.append([hop_number + 1, ip, prefix, asn, status.capitalize()])

		if outfolder:
			df = pd.DataFrame(data=raw_data, columns=["hop", "ip", "prefix", "asn", "status"], dtype=str)
			data_path = os.path.join(outfolder, "data")
			if not os.path.exists(data_path):
				os.mkdir(data_path)
			df.to_csv(os.path.join(data_path, f"{target_ip}.csv"), index=False)

			# ({trace_data['completed'] and 'Successful' or 'Unsuccessful'})
			target_str = (target_ip == trace_data["destination_ip"] and target_ip) or f"{target_ip} ({trace_data['destination_ip']})"
			caption = f"The results from a traceroute to {target_str}."
			label = f"tab:table-{target_str}"
			raw_data.append("Traceroute was " + (trace_data["completed"] and "successful" or "unsuccessful"))
			tex = create_latex_table(["Hop", "IP", "Prefix", "AS", "RPKI Status"], raw_data, caption, label)
			
			table_path = os.path.join(outfolder, "latex_tables")
			if not os.path.exists(table_path):
				os.mkdir(table_path)

			with open(os.path.join(table_path, f"{target_ip}.tex"), "w") as f:
				f.write(tex)

			# summary.append([target_ip, len(unique_prefixes), num_valid, num_invalid, num_notfound])
			summary.loc[len(summary), summary.columns] = target_ip, trace_data['destination_ip'], len(unique_prefixes), num_valid, num_invalid, num_notfound, len(hop_list), trace_data["completed"]
			# summary.loc[len(summary), summary.columns] = None, None, None, None, None

		all_raw_data.append(raw_data)

	if outfolder:
		summary.to_csv(os.path.join(outfolder, f"rpki_summary.csv"), index=False)

	logger.info(f"Finished tracing and validating list of {len(ip_list)} ip(s).")
	return all_raw_data


# https://superuser.com/questions/355486/what-is-the-range-of-ports-that-is-usually-used-in-the-traceroute-command
# https://github.com/robertdavidgraham/masscan


#######################################################
# Initialization ######################################
#######################################################
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

parser = HelpParser(
	prog="tracer.py",
	description="description",
	epilog=None
)

parser.add_argument("outfolder", type=str, help="A folder to put output data in.")
parser.add_argument("--infile", type=str, help="A path to a list of IPs.")
parser.add_argument("--column", type=str, help="The column to get URLs from if a .csv is provided as an infile.")
parser.add_argument("--ip", action="append", type=str, help="Used to specify an IP to process, with or without an infile.")
parser.add_argument("--nomultiprocessing", action="store_true", help="Forces the program to do the traceroutes individually instead of using multiple processes.")
#parser.add_argument("--as", action="store_true", help="Map an IP address to an AS")

if __name__ == "__main__":
	args = parser.parse_args()

	if sys.platform == "win32":
		# Windows
		pass
	elif sys.platform == "darwin":
		# OS X
		logging.error(f"Not supported for platform: {sys.platform}")
		exit(1)

	elif sys.platform == "linux" or sys.platform == "linux":
		# Linux
		logging.error(f"Not supported for platform: {sys.platform}")
		exit(1)

	else:
		logging.error(f"Unknown platform: {sys.platform}")
		exit(1)

	vargs = vars(args)
	logger.debug("Launched with arguments: %s", vargs)

	IPs = []
	if args.ip:
		IPs += args.ip

	if args.infile:
		IPs += get_IPs_from_file(args.infile, args.column)

	if len(IPs) == 0:
		logger.error("No IPs specified.")
		exit(0)

	main(IPs, outfolder=args.outfolder, multiprocessing=not args.nomultiprocessing)


