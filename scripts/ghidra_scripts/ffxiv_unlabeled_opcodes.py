# Find and print the list of opcodes (as hex strings / JSON)
# @category __UserScripts
# @menupath Tools.Scripts.ffxiv_unlabeled_opcodes
# @runtime PyGhidra

import typing
if typing.TYPE_CHECKING:
	from ghidra.ghidra_builtins import *

import json

memory = currentProgram.memory
min_address = currentProgram.minAddress
symbol_table = currentProgram.symbolTable
listing = currentProgram.listing

pattern = bytes.fromhex("""
49 8b 40 10
4c 8b 50 38
41 0f b7 42 02
83 c0 9a
3d 81 03 00 00
0f 87 1b 29 00 00
4c 8d 1d be 31 fe fd
48 98
45 8b 8c 83 58 f7 01 02
4d 03 cb
41 ff e1
""")
mask = bytes.fromhex("""
f8 ff f8 00
f8 ff f8 00
f8 ff ff f8 00
ff ff 00
ff 00 00 00 00
ff ff 00 00 00 00
f8 ff ff 00 00 00 00
f8 ff
f8 ff ff 00 00 00 00 00
f8 ff ff
f8 ff ff
""")

found = memory.findBytes(min_address, pattern, mask, True, monitor)
if not found:
	raise Exception("Pattern not found")
function = getFunctionAt(found)
if not function and askYesNo(
	"Function not regististered as such by Ghidra",
	"For convenience a full auto-analysis can be skipped, and only the relevant function can be disassembled (and auto-analyzed).  Proceed?"):
	disassembled = disassemble(found)
	if not disassembled:
		raise Exception("Failed to disassemble")
	function = createFunction(found, None)
	analyzeChanges(currentProgram)
if not function:
	raise Exception("Failed to find function")

opcodes: list[str] = []
instructions = listing.getInstructions(function.body, True)
for instr in instructions:
	symbols = symbol_table.getSymbols(instr.address)
	if len(symbols) == 1:
		symbol_name_parts = symbols[0].name.split('_')
		if symbol_name_parts[0] == "caseD":
			opcode = int(symbol_name_parts[1], 16)
			opcodes.append(hex(opcode))

print(json.dumps(opcodes))
