import json, logging, re
import urllib.request

from ffxiv_opcodes.ffxiv_versions import Region


FFXIVOPCODES_GITHUB_COMMITS_API_URL_TEMPLATE = "https://api.github.com/repos/karashiiro/FFXIVOpcodes/commits?path=FFXIVOpcodes/Ipcs.cs&until={date}&per_page=1"
FFXIVOPCODES_IPCS_FILE_URL_TEMPLATE = "https://raw.githubusercontent.com/karashiiro/FFXIVOpcodes/{commit_identifier}/FFXIVOpcodes/Ipcs{region_suffix}.cs"
#FFXIVOPCODES_CONSTANTS_FILE_URL_TEMPLATE = "https://raw.githubusercontent.com/karashiiro/FFXIVOpcodes/{commit_identifier}/FFXIVConstants/{constants_file_name}.cs"

CONSTANTS_DIFF_PREFIX = """diff --git a/FFXIVConstants/TW.cs b/FFXIVConstants/TW.cs
--- a/FFXIVConstants/TW.cs
+++ b/FFXIVConstants/TW.cs
@@ -7,7 +7,7 @@ namespace FFXIVConstants
         public static Dictionary<string, object> Constants = new Dictionary<string, object>
         {
             // This is InventoryModifyHandler + 7
"""
CONSTANTS_DIFF_SUFFIX = """         };
     }
 }
"""

SERVER_ZONE_IPCS_DIFF_PREFIX_TEMPLATE = """diff --git a/FFXIVOpcodes/Ipcs_tw.cs b/FFXIVOpcodes/Ipcs_tw.cs
--- a/FFXIVOpcodes/Ipcs_tw.cs
+++ b/FFXIVOpcodes/Ipcs_tw.cs
@@ -{old_line_start},{old_line_count} +{new_line_start},{new_line_count} @@ namespace FFXIVOpcodes.TW
     */
     enum ServerZoneIpcType : ushort
     {{
"""
SERVER_ZONE_IPCS_DIFF_SUFFIX = """     };
 
     /**
"""

CLIENT_ZONE_IPCS_DIFF_PREFIX_TEMPLATE = """@@ -{old_line_start},{old_line_count} +{new_line_start},{new_line_count} @@ namespace FFXIVOpcodes.TW
     */
     enum ClientZoneIpcType : ushort
     {{
"""
CLIENT_ZONE_IPCS_DIFF_SUFFIX = """     };
 
     enum ServerChatIpcType : ushort
"""

OPCODE_DEFINITION_REGEX = re.compile(r"(?P<prefix>\s+)(?P<opcode_name>[A-Z]\w+) = (?P<opcode_value>0x[0-9A-Z]{4,}), // updated (?P<version_name>\d.\d\d?([a-z]\d?)?)(?P<suffix>\s+)")


def region_suffix(region: Region) -> str:
	match region:
		case Region.GLOBAL:
			return ""
		case _:
			return f"_{region}"

def constants_file_name(region: Region) -> str:
	match Region:
		case Region.GLOBAL:
			return "Global"
		case _:
			return str(region).upper()


def fetch_last_commit_hash_before_date(date: str) -> str:
	commits_api_url = FFXIVOPCODES_GITHUB_COMMITS_API_URL_TEMPLATE.format(date = date)
	with urllib.request.urlopen(commits_api_url) as response:
		return json.loads(response.read().decode())[0]["sha"]

def fetch_ffxivopcodes_ipcs_file(region: Region, commit_identifier = "refs/heads/master") -> str:
	ipcs_file_url = FFXIVOPCODES_IPCS_FILE_URL_TEMPLATE.format(commit_identifier = commit_identifier, region_suffix = region_suffix(region))
	with urllib.request.urlopen(ipcs_file_url) as response:
		return response.read().decode()

def generate_diff_dict(old: list[str], new: list[str]) -> dict[int, int]:
	out: dict[int, int] = dict()
	for (old, new) in zip(old, new):
		out[int(old, base=0)] = int(new, base=0)
	return out

def apply_diff_to_ipcs_file(diff: dict[int, int], ipcs: str, version_name = "FIXME") -> tuple[list[str], int]:
	lines: list[str] = []
	inventory_modify_handler_opcode: int | None = None

	for line in ipcs.splitlines(keepends=True):
		matches = OPCODE_DEFINITION_REGEX.fullmatch(line)
		if matches is not None:
			opcode_name = matches["opcode_name"]
			old_opcode_value = int(matches["opcode_value"], base=0)
			new_opcode_value = diff[old_opcode_value]

			lines.append(f"{matches["prefix"]}{opcode_name} = 0x{new_opcode_value:04X}, // updated {version_name}{matches["suffix"]}")

			if opcode_name == "InventoryModifyHandler":
				inventory_modify_handler_opcode = new_opcode_value
		else:
			lines.append(line)

	if inventory_modify_handler_opcode is None:
		raise Exception("Failed to find opcode of `InventoryModifyHandler`")

	return (lines, inventory_modify_handler_opcode)

def find_matching_line(pattern: str, lines: list[str], start=0) -> int:
	for (i, line) in enumerate(lines[start:], start):
		if pattern in line:
			return i

	raise Exception(f"Failed to find pattern `{pattern}` in lines")

COMMENTED_OUT_REGEX = re.compile(r"^\s*//")

class NaiveHunk:
	prefix: str
	removed_lines: list[str]
	added_lines: list[str]
	suffix: str

	def __init__(self, suffix: str):
		self.prefix = ""
		self.removed_lines = list()
		self.added_lines = list()
		self.suffix = suffix

def generate_git_diff(modified_lines: list[str], modified_inventory_modify_handler_opcode: int, current_ipcs: str) -> str:
	current_inventory_modify_handler_opcode: int | None = None

	current_lines = current_ipcs.splitlines(keepends=True)

	server_zone_ipc_diff = NaiveHunk(SERVER_ZONE_IPCS_DIFF_SUFFIX)
	client_zone_ipc_diff = NaiveHunk(CLIENT_ZONE_IPCS_DIFF_SUFFIX)
	line_count_delta = 0
	for (start_pattern, prefix_template, diff) in [
		("enum ServerZoneIpcType : ushort", SERVER_ZONE_IPCS_DIFF_PREFIX_TEMPLATE, server_zone_ipc_diff),
		("enum ClientZoneIpcType : ushort", CLIENT_ZONE_IPCS_DIFF_PREFIX_TEMPLATE, client_zone_ipc_diff),
	]: 
	
		current_ipcs_line_idx = find_matching_line(start_pattern, current_lines) + 2
		current_ipcs_end_idx = find_matching_line("}", current_lines, current_ipcs_line_idx)
		for line in current_lines[current_ipcs_line_idx:current_ipcs_end_idx]:
			diff.removed_lines.append(line)

			matches = OPCODE_DEFINITION_REGEX.fullmatch(line)
			if matches is not None and matches["opcode_name"] == "InventoryModifyHandler":
				current_inventory_modify_handler_opcode = int(matches["opcode_value"], base=0)

		modified_ipcs_line_idx = find_matching_line(start_pattern, modified_lines) + 2
		modified_ipcs_end_idx = find_matching_line("}", modified_lines, modified_ipcs_line_idx)
		skipped_modified_lines = 0
		for line in modified_lines[modified_ipcs_line_idx:modified_ipcs_end_idx]:
			if COMMENTED_OUT_REGEX.match(line):
				skipped_modified_lines += 1
			else:
				diff.added_lines.append(line)

		diff.prefix = prefix_template.format(old_line_start = current_ipcs_line_idx, old_line_count = 3 + len(diff.removed_lines) + 3, new_line_start = current_ipcs_line_idx + line_count_delta, new_line_count = 3 + len(diff.added_lines) + 3)
		line_count_delta += len(diff.added_lines) - len(diff.removed_lines)

	if current_inventory_modify_handler_opcode is None:
			raise Exception("Failed to find current opcode of `InventoryModifyHandler`") 
	output_diff = ''.join([
		CONSTANTS_DIFF_PREFIX,
		# MAYBE: test if line endings matter here since we don't copy them from the source file here
		f"-            {{ \"InventoryOperationBaseValue\", 0x{current_inventory_modify_handler_opcode:04X}+7 }}\n",
		f"+            {{ \"InventoryOperationBaseValue\", 0x{modified_inventory_modify_handler_opcode:04X}+7 }}\n",
		CONSTANTS_DIFF_SUFFIX,
		server_zone_ipc_diff.prefix,
		''.join(f"-{line}" for line in server_zone_ipc_diff.removed_lines),
		''.join(f"+{line}" for line in server_zone_ipc_diff.added_lines),
		server_zone_ipc_diff.suffix,
		client_zone_ipc_diff.prefix,
		''.join(f"-{line}" for line in client_zone_ipc_diff.removed_lines),
		''.join(f"+{line}" for line in client_zone_ipc_diff.added_lines),
		client_zone_ipc_diff.suffix,
	])

	return output_diff
