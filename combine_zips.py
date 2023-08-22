
import requests

import glob
import json
import math
import os
import shutil
import zipfile

x = {}
x.get()

# https://superuser.com/questions/1104504/windows-batch-extract-zip-files-into-folders-based-on-zip-name-and-combining-si

zips = glob.glob("rpki_zips/*.zip")

for path in zips:
	zip = zipfile.ZipFile(path)

	zip.extractall("rpki_zips/all")

shutil.make_archive(f"rpki_zips/all", "zip", "rpki_zips/all")