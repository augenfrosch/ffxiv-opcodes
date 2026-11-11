import argparse, logging

from ffxiv_opcodes.extract_opcode_list import run_pyghidra_script


def main() -> None:
	logging.basicConfig(format="[%(levelname)s] %(message)s", level=logging.DEBUG)

	parser = argparse.ArgumentParser()
	subparsers = parser.add_subparsers(dest="subcommand", required=True)
	subparser = subparsers.add_parser("extract-opcode-list")
	subparser.add_argument("-g", "--ghidra-install-dir", default=None)
	subparser.add_argument("-i", "--input", required=True)
	subparser.add_argument("-o", "--output", default="out.json")

	args = parser.parse_args()

	logging.debug(f"args={args}")
	match args.subcommand:
		case "extract-opcode-list":
			(stdout, stderr) = run_pyghidra_script(args.ghidra_install_dir, args.input)

			logging.debug(f"stderr=\"{stderr}\"")

			print(stdout, end="", file=open(args.output, "w"), flush=True)


if __name__ == "__main__":
	main()
