import json, re
from dataclasses import dataclass
from enum import StrEnum
from types import SimpleNamespace
import urllib.request


GAME_VERSION_NAME_RE = re.compile(r"^(?P<expansion>\d).(?P<major_patch>\d)(?P<minor_patch>\d)?(?P<hotfix_suffix>h\d?|x\d|[a-g])?$")
FFXIV_VERSION_LIST_JSON_URL_TEMPLATE = "https://raw.githubusercontent.com/augenfrosch/ffxiv-versions/refs/heads/main/data/json/{region}.json"

class Region(StrEnum):
	GLOBAL = "global"
	CN = "cn"
	KR = "kr"
	TW = "tw"

@dataclass
class Version:
	game_version: str
	version_name: str
	release_date: str
	patch_note_url: str
	update_notice_url: str

@dataclass(order=True)
class VersionName:
	expansion: int
	major_patch: int
	minor_patch: int
	public_hotfix: int 

	def __init__(self, s: str):
		matches = GAME_VERSION_NAME_RE.match(s)
		self.expansion = int(matches["expansion"])
		self.major_patch = int(matches["major_patch"])
		self.minor_patch = int(matches["minor_patch"]) if matches["minor_patch"] is not None else 0
		hotfix_suffix = matches["hotfix_suffix"]
		if hotfix_suffix is None:
			self.public_hotfix = 0
		else:
			match ord(hotfix_suffix[0]):
				case c if c == ord("h"):
					self.public_hotfix = int(hotfix_suffix[1]) if len(hotfix_suffix) > 1 else 1
				case c if c == ord("x"):
					self.public_hotfix = int(hotfix_suffix[1])
				case c if ord("a") <= c < ord("h"):
					self.public_hotfix = c - ord("a") + 1


def find_next_version_release_date(version_list: list[Version], version_name: str, region: Region = Region.GLOBAL) -> str:
	game_version = VersionName(version_name)

	for version in version_list:
		current_version = VersionName(version.version_name)
		if current_version > game_version:
			return version.release_date

	raise Exception(f"Failed to find release date for version after `{version_name}`")


def fetch_version_list(region: Region = Region.GLOBAL) -> list[Version]:
	version_list_url = FFXIV_VERSION_LIST_JSON_URL_TEMPLATE.format(region = region)
	with urllib.request.urlopen(version_list_url) as response:
		return json.loads(response.read().decode(), object_hook=lambda d: SimpleNamespace(**d))
		