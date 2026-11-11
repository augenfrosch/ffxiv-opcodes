import logging, tempfile

from pathlib import Path

import pyghidra

def run_pyghidra_script(ghidra_install_dir: str | None, input_file_path: str) -> tuple[str, str]:
	pyghidra.start(ghidra_install_dir)

	with tempfile.TemporaryDirectory() as temp_dir, pyghidra.open_project(temp_dir, "tmp_ffxiv_extract", create=True) as project:
		logging.debug(f"temp_dir={temp_dir}")

		loader = pyghidra.program_loader().project(project)
		loader.source(input_file_path)

		logging.info(f"Loading `{input_file_path}`")
		load_results = loader.load()
		program = load_results.primaryDomainObject

		logging.info("Running `ffxiv_unlabeled_opcodes.py`")

		return pyghidra.ghidra_script(Path(__file__).parent.parent.parent.joinpath("scripts", "ghidra_scripts", "ffxiv_unlabeled_opcodes.py"), project, program, echo_stdout=False, echo_stderr=False)
