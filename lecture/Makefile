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

.PHONY: all script students slides falstad ch publish sync clean

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

# Push the sources to lecture/ in the GitHub repo (build output is skipped
# via .gitignore). Keeps a clone in SYNC_DIR; e.g. make sync MSG="Fix ADC"
SYNC_REPO ?= git@github.com:mopfeil/Circuit_Analysis.git
SYNC_KEY  ?= $(HOME)/.ssh/circuit_analysis_deploy
SYNC_DIR  ?= $(HOME)/.cache/circuit_analysis_sync
SYNC_GIT   = git -C $(SYNC_DIR)
MSG       ?= Update lecture sources

sync:
	test -d $(SYNC_DIR)/.git || GIT_SSH_COMMAND="ssh -i $(SYNC_KEY) -o IdentitiesOnly=yes" git clone $(SYNC_REPO) $(SYNC_DIR)
	$(SYNC_GIT) config core.sshCommand "ssh -i $(SYNC_KEY) -o IdentitiesOnly=yes"
	$(SYNC_GIT) config user.name >/dev/null || $(SYNC_GIT) config user.name "Markus Pfeil"
	$(SYNC_GIT) config user.email >/dev/null || $(SYNC_GIT) config user.email "31349746+mopfeil@users.noreply.github.com"
	$(SYNC_GIT) pull --ff-only
	rsync -a --delete --exclude-from=.gitignore ./ $(SYNC_DIR)/lecture/
	$(SYNC_GIT) add -A lecture
	$(SYNC_GIT) diff --cached --quiet || { $(SYNC_GIT) commit -m "$(MSG)" && $(SYNC_GIT) push; }

clean:
	latexmk -c docu.tex slides.tex
	latexmk -c -jobname=docu_students docu.tex
	rm -rf build
