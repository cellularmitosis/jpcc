	.section __TEXT,__text,regular,pure_instructions
	.section __TEXT,__picsymbolstub1,symbol_stubs,pure_instructions,32
	.machine ppc
	.text
	.align 2
	.globl _main
_main:
	stmw r30,-8(r1)
	stwu r1,-48(r1)
	mr r30,r1
	li r0,2
	mr r3,r0
	lwz r1,0(r1)
	lmw r30,-8(r1)
	blr
