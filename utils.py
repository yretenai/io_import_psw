from bpy.types import Context, Object
from glob import glob
from numpy import ndarray
from os.path import sep
from pathlib import Path
import bpy
import numpy
import os.path


def find_root_from_path(path: str):
	current_path = Path(path).parent.absolute()
	while True:
		root_files = glob(str(current_path) + sep + "*.root")
		if len(root_files) == 1:
			log_info('PSW', "Found root path %s" % str(current_path))
			if os.path.exists(f"{str(current_path)}/Content"):
				log_info('PSW', "Root is modern layout")
				return str(current_path) + '/Content'
			return str(current_path)
		if current_path.parent == current_path:
			return None
		current_path = current_path.parent


def fix_string(string: str) -> str:
	return string.rstrip(b'\0').decode(errors='replace', encoding='utf8')


def fix_string_np(string: ndarray) -> str:
	return numpy.trim_zeros(string).tobytes().decode(errors='replace', encoding='utf8')

INFO = u"\u001b[35m"
ERROR = u"\u001b[31m"
WARNING = u"\u001b[33m"
RESET = u"\u001b[0m"

def log_info(category: str, message: str):
	print(f'{INFO}[{category}]{RESET} {message}')


def log_error(category: str, message: str):
	print(f'{ERROR}[{category}]{RESET} {message}')

def log_warning(category: str, message: str):
	print(f'{WARNING}[{category}]{RESET} {message}')
