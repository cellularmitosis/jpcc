	.section __TEXT, __text,regular,pure_instructions
	.section __TEXT, __picsymbolstub1,symbol_stubs,pure_instructions,32
	.machine ppc
	.text
	.align 2
	.globl _main
_main:
	li r3, 2
	blr
