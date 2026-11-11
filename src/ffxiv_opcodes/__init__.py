import argparse, logging, os, tempfile

import pyghidra

def run_script(ghidra_install_dir: str | None, input_file_path: str) -> tuple[str, str]:
	pyghidra.start(ghidra_install_dir)

	with tempfile.TemporaryDirectory() as temp_dir, pyghidra.open_project(temp_dir, "tmp_ffxiv_extract", create=True) as project:
		logging.debug(f"temp_dir={temp_dir}")

		loader = pyghidra.program_loader().project(project)
		loader.source(input_file_path)

		logging.info(f"Loading `{input_file_path}`")
		load_results = loader.load()
		program = load_results.primaryDomainObject

		logging.info("Running `ffxiv_unlabeled_opcodes.py`")

		return pyghidra.ghidra_script(os.path.join(os.path.dirname(__file__), "ffxiv_unlabeled_opcodes.py"), project, program, echo_stdout=False, echo_stderr=False)


def main() -> None:
	logging.basicConfig(format="[%(levelname)s] %(message)s", level=logging.DEBUG)

	parser = argparse.ArgumentParser()
	parser.add_argument("-g", "--ghidra-install-dir", default=None)
	parser.add_argument("-i", "--input", required=True)
	parser.add_argument("-o", "--output", default="out.json")

	args = parser.parse_args()

	logging.debug(f"args={args},{os.getcwd()},{os.environ["UV_WORKING_DIR"]}")

	(stdout, stderr) = run_script(args.ghidra_install_dir, args.input)

	logging.debug(f"stderr=\"{stderr}\"")

	print(stdout, end="", file=open(args.output, "w"), flush=True)


if __name__ == "__main__":
	main()
