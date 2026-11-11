import argparse, logging

from ffxiv_opcodes.extract_opcode_list import run_pyghidra_script
from ffxiv_opcodes.opcodediff import find_global_opcodes_for_opcode_count, fetch_global_opcode_list, generate_opcode_diff


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
	subparser.add_argument("-f", "--format", default="opcodediff-json", choices=["opcodediff-json", "git-diff"])
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

			(version, global_opcodes) = find_global_opcodes_for_opcode_count(len(opcodes)) if args.global_version_name is None else (args.global_version_name, fetch_global_opcode_list(args.global_version_name))

			match args.format:
				case "opcodediff-json":
					json.dump(generate_opcode_diff(global_opcodes, opcodes), open(args.output, "w"), indent="\t", default=lambda o: o.__dict__)
				case "git-diff":
					raise NotImplementedError("`git-diff`output format is not yet implemented") # TODO
				


if __name__ == "__main__":
	main()
