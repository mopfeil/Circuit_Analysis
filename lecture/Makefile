# Build the lecture script (docu.pdf), the script without solutions
# (docu_students.pdf) and the slides (slides.pdf).
# Requires TeX Live with latexmk and lualatex, and python3 with numpy for
# the Falstad examples. The RWU font Barlow Semi Condensed is shipped in
# fonts/ and needs lualatex; "make PDFTEX=1" builds with pdflatex instead.

ifdef PDFTEX
LATEXMK = latexmk -pdf -interaction=nonstopmode -halt-on-error
else
LATEXMK = latexmk -lualatex -interaction=nonstopmode -halt-on-error
endif

.PHONY: all script students slides falstad ch publish clean

all: falstad script students slides

# generate examples/*/*.txt and falstadlinks.tex, simulate and check all circuits
falstad:
	python3 falstad/build_all.py

script:
	$(LATEXMK) docu.tex

students:
	$(LATEXMK) -jobname=docu_students -usepretex='\def\nosolutions{}' docu.tex

slides:
	$(LATEXMK) slides.tex

# one chapter only, e.g. make ch CH=Bridges  -> build/ch-Bridges-*.pdf
ch:
	$(LATEXMK) -outdir=build -jobname=ch-$(CH)-script -usepretex='\def\onlychapter{$(CH)}' docu.tex
	$(LATEXMK) -outdir=build -jobname=ch-$(CH)-slides -usepretex='\def\onlychapter{$(CH)}' slides.tex

# Copy the built PDFs into pdf/
publish: all
	mkdir -p pdf
	cp docu.pdf pdf/CircuitDesign_Script.pdf
	cp docu_students.pdf pdf/CircuitDesign_Script_Students.pdf
	cp slides.pdf pdf/CircuitDesign_Slides.pdf

clean:
	latexmk -c docu.tex slides.tex
	latexmk -c -jobname=docu_students docu.tex
	rm -rf build
