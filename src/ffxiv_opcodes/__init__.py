import argparse, logging

from ffxiv_opcodes.extract_opcode_list import run_pyghidra_script
from ffxiv_opcodes.ffxiv_versions import Region, fetch_version_list, find_next_version_release_date
from ffxiv_opcodes.ffxivopcodes import apply_diff_to_ipcs_file, fetch_ffxivopcodes_ipcs_file, fetch_last_commit_hash_before_date, generate_diff_dict, generate_git_diff
from ffxiv_opcodes.opcodediff import find_latest_global_opcodes_for_opcode_count, fetch_global_opcode_list, generate_opcode_diff


def main() -> None:
	parser = argparse.ArgumentParser()
	parser.add_argument("-v", "--verbose", action="store_true")
	subparsers = parser.add_subparsers(dest="subcommand", required=True)

	subparser = subparsers.add_parser("extract-opcode-list")
	subparser.add_argument("-g", "--ghidra-install-dir", default=None)
	subparser.add_argument("-i", "--input", required=True)
	subparser.add_argument("-o", "--output", default="out.json")

	subparser = subparsers.add_parser("generate-cross-version-diff")
	subparser.add_argument("-i", "--input", required=True)
	subparser.add_argument("-g", "--global-version-name", default=None)
	subparser.add_argument("-f", "--format", default="git-diff", choices=["opcodediff-json", "git-diff"])
	subparser.add_argument("-o", "--output", required=True)

	args = parser.parse_args()


	logging.basicConfig(format="[%(levelname)s] %(message)s", level=(logging.DEBUG if args.verbose else logging.INFO))

	logging.debug(f"args={args}")
	match args.subcommand:
		case "extract-opcode-list":
			(stdout, stderr) = run_pyghidra_script(args.ghidra_install_dir, args.input)

			logging.debug(f"stderr=\"{stderr}\"")

			print(stdout, end="", file=open(args.output, "w"), flush=True)
		case "generate-cross-version-diff":
			import json
			opcodes: list[str] = json.load(open(args.input))

			(version, global_opcodes) = find_latest_global_opcodes_for_opcode_count(len(opcodes)) if args.global_version_name is None else (args.global_version_name, fetch_global_opcode_list(args.global_version_name))

			match args.format:
				case "opcodediff-json":
					json.dump(generate_opcode_diff(global_opcodes, opcodes), open(args.output, "w"), indent="\t", default=lambda o: o.__dict__)
				case "git-diff":
					diff = generate_diff_dict(global_opcodes, opcodes)

					next_version_release_date = find_next_version_release_date(fetch_version_list(), version)
					logging.debug(f"next_version_release_date={next_version_release_date}")
					latest_relevant_ffxivopcodes_commit_hash = fetch_last_commit_hash_before_date(next_version_release_date)
					logging.debug(f"next_version_ffxivopcodes_commit={latest_relevant_ffxivopcodes_commit_hash}")

					global_ipcs_file = fetch_ffxivopcodes_ipcs_file(Region.GLOBAL, commit_identifier=latest_relevant_ffxivopcodes_commit_hash)
					# MAYBE: don't hardcode region? There hasn't been a CN or KR exclusive hotfix since they synced up + a normal diff should work for them
					latest_tw_ipcs_file = fetch_ffxivopcodes_ipcs_file(Region.TW)
					# MAYBE: add sth to the effect of a `new-version-name` argument
					(lines, inventory_modify_handler_opcode) =  apply_diff_to_ipcs_file(diff, global_ipcs_file)
					logging.debug(f"inventory_modify_handler_opcode=0x{inventory_modify_handler_opcode:04X}")

					# MAYBE also update the version definition?
					print(generate_git_diff(lines, inventory_modify_handler_opcode, latest_tw_ipcs_file), end="", file=open(args.output, "w"), flush=True)


if __name__ == "__main__":
	main()
