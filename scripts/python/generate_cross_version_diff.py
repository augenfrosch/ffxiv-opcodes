#!/usr/bin/env python3
"""Generates an opcode diff accross versions via xivdev/opcodediff that can be used with FFXIVOpcode's global_import.py"""

import json
import sys
import urllib.request
from dataclasses import dataclass
from typing import Optional

GLOBAL_VERSIONS_URL = "https://github.com/xivdev/opcodediff/raw/refs/heads/main/automation/ffxiv_versions_global.json"
DIFF_URL = "https://raw.githubusercontent.com/xivdev/opcodediff/refs/heads/main/diffs/{version}.diff.json"

@dataclass
class Diff:
	old: list[str]
	new: list[str]


@dataclass
class Version:
	retail_version: str
	version_string: str

def fetch_diffs(version: str) -> list[Diff]:
	with urllib.request.urlopen(DIFF_URL.format(version = version)) as r:
		return [Diff(**diff) for diff in json.loads(r.read())]
	
def diffs_to_reverse_mapping(diffs: list[Diff]) -> dict[str, Optional[str]]:
	mapping: dict[str, Optional[str]] = dict()
	for diff in diffs:
		if len(diff.old) == 0:
			mapping[diff.new[0]] = None
		elif len(diff.new) == 1:
			mapping[diff.new[0]] = diff.old[0]
		else:
			# TODO: look into this a bit more maybe just blacklist / obfuscation related. Could affect order, see comment below
			print(f"[WARN] Diff shows an opcode being deleted: {diff.old[0]}; no mapping will be created", file=sys.stderr)
	return mapping

def combine_reverse_mappings(newer: dict[str, Optional[str]], older: dict[str, Optional[str]]) -> dict[str, Optional[str]]:
	mapping: dict[str, Optional[str]] = dict()
	for (new, old) in newer.items():
		if old == None:
			mapping[new] = None
		else:
			mapping[new] = older[old]
	return mapping

def fetch_global_versions() -> list[Version]:
	with urllib.request.urlopen(GLOBAL_VERSIONS_URL) as r:
		return [Version(**version) for version in json.loads(r.read())]

def read_opcodes(path: str) -> list[str]:
	with open(path) as f:
		return json.load(f)

def new_opcodes(diffs: list[Diff]) -> list[str]:
	new_opcodes = []
	for diff in diffs:
		if len(diff.new) != 0:
			new_opcodes.append(diff.new[0])
	return new_opcodes

def generate_diffs(reverse_mapping: dict[str, Optional[str]], target_opcodes: list[str]) -> list[Diff]:
	# TODO: check that the order of opcodes actually stays consistent between versions
	diffs: list[Diff] = list()

	opcode_idx = 0
	for (global_opcode, old_opcode) in reverse_mapping.items():
		if old_opcode != None:
			diffs.append(Diff(old=[global_opcode], new=[target_opcodes[opcode_idx]]))
			opcode_idx += 1
		else:
			diffs.append(Diff(old=[global_opcode], new=[]))
	
	# 7.3 deletes an opcode according to the diff. The assert in `main`` is what should hold true
	#assert opcode_idx == len(target_opcodes)

	return diffs


def main():
	if len(sys.argv) < 2:
		print(f"Usage: {sys.argv[0]} <version> <data>")
		print(f"  e.g. {sys.argv[0]} 7.25h3 data/tw.json")
		sys.exit(1)
	target_version = sys.argv[1]
	target_opcodes = read_opcodes(sys.argv[2])

	global_versions = fetch_global_versions()
	global_versions.reverse()
	global_versions = [version.retail_version for version in global_versions]

	global_version = global_versions[0]
	print(f"[INFO] Version: {global_version}", file=sys.stderr)
	diffs = fetch_diffs(global_version)
	reverse_mapping = diffs_to_reverse_mapping(diffs)
	for global_version in global_versions[1:global_versions.index(target_version)+1]:
		print(f"[INFO] Version: {global_version}", file=sys.stderr)
		diffs = fetch_diffs(global_version)
		next_mapping = diffs_to_reverse_mapping(diffs)
		reverse_mapping = combine_reverse_mappings(reverse_mapping, next_mapping)

	assert len(target_opcodes) == len(new_opcodes(diffs))

	generated_diffs = generate_diffs(reverse_mapping, target_opcodes)

	print(json.dumps(generated_diffs, default=lambda o: o.__dict__))


if __name__ == "__main__":
	main()