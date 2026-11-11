from dataclasses import dataclass

import json, logging
from types import SimpleNamespace
import urllib.request


OPCODEDIFF_FFXIV_GLOBAL_VERSION_JSON_URL = "https://github.com/xivdev/opcodediff/raw/refs/heads/main/automation/ffxiv_versions_global.json"
OPCODEDIFF_PATCH_DIFF_JSON_URL_TEMPLATE = "https://github.com/xivdev/opcodediff/raw/refs/heads/main/diffs/{version}.diff.json"

@dataclass
class Version:
	retail_version: str
	version_string: str

@dataclass
class Diff:
	old: list[str]
	new: list[str]


def find_global_opcodes_for_opcode_count(opcode_count: int) -> tuple[str, list[str]]:
	logging.info(f"Searching for global version with matching opcode count: {opcode_count}")
	with urllib.request.urlopen(OPCODEDIFF_FFXIV_GLOBAL_VERSION_JSON_URL) as response:
		versions: list[Version] = json.loads(response.read().decode(), object_hook=lambda d: SimpleNamespace(**d))

		# TODO: This should probably just be a course search over the last minor patch/hotfix for each major patch
		for version in reversed(versions):
			opcodes = fetch_global_opcode_list(version.retail_version)
			logging.debug(f"version={version},len(opcodes)={len(opcodes)}")

			if len(opcodes) == opcode_count:
				logging.info(f"Found version: {version}")
				return (version.retail_version, opcodes)

	raise Exception(f"Failed to find opcodes of version with {opcode_count} opcodes")

def fetch_global_opcode_list(version_name: str) -> list[str]:
	patch_diff_json_url = OPCODEDIFF_PATCH_DIFF_JSON_URL_TEMPLATE.format(version = version_name)
	with urllib.request.urlopen(patch_diff_json_url) as response:
		opcodediff: list[Diff] = json.loads(response.read().decode(), object_hook=lambda d: SimpleNamespace(**d))
		return [diff.new[0] for diff in opcodediff if len(diff.new) > 0]

def generate_opcode_diff(old: list[str], new: list[str]) -> list[Diff]:
	assert len(old) == len(new)
	return [Diff([old], [new]) for (old, new) in zip(old, new)]
