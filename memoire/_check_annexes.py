"""Verification statique des annexes reecrites (2026-08-31).

Ne remplace pas une compilation. Verifie trois choses.
  1. Toute macro de chiffres.tex citee dans une annexe est bien definie.
  2. Les environnements ouverts sont refermes, et les accolades sont equilibrees.
  3. Tout \\label de flottant d'annexe est cite par un \\ref quelque part.
"""
import glob
import re

ROOT = "."
CH = open(ROOT + "/chiffres.tex", encoding="utf-8").read()
DEFINED = set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", CH))
PREFIXES = ("mes", "obs", "calib", "pros", "grille", "regret", "front")

annexes = sorted(glob.glob(ROOT + "/annexes/*.tex"))
allsrc = {f: open(f, encoding="utf-8").read() for f in annexes}
corps = {f: open(f, encoding="utf-8").read()
         for f in sorted(glob.glob(ROOT + "/chapitres/*.tex"))}

problems = []

# 1. macros
for f, txt in allsrc.items():
    for name in set(m[1:] for m in re.findall(r"\\[A-Za-z]+", txt)):
        if name.startswith(PREFIXES) and name not in DEFINED:
            problems.append("macro non definie dans chiffres.tex : %s (%s)" % (name, f))

# 2. environnements et accolades
for f, txt in allsrc.items():
    stack = []
    for kind, env in re.findall(r"\\(begin|end)\{([A-Za-z*]+)\}", txt):
        if kind == "begin":
            stack.append(env)
        else:
            if not stack or stack[-1] != env:
                problems.append("environnement mal imbrique : end{%s} (%s)" % (env, f))
                break
            stack.pop()
    if stack:
        problems.append("environnement non referme : %s (%s)" % (stack, f))
    stripped = re.sub(r"\\[{}]", "", txt)
    if stripped.count("{") != stripped.count("}"):
        problems.append("accolades desequilibrees : %+d (%s)"
                        % (stripped.count("{") - stripped.count("}"), f))

# 3. flottants cites
refs = set()
for txt in list(allsrc.values()) + list(corps.values()):
    refs |= set(re.findall(r"\\(?:ref|eqref)\{([^}]+)\}", txt))
for f, txt in allsrc.items():
    for lab in re.findall(r"\\label\{((?:tab|fig):[^}]+)\}", txt):
        if lab not in refs:
            problems.append("flottant jamais cite : %s (%s)" % (lab, f))

# 4. ponctuation proscrite hors tableaux techniques
for f, txt in allsrc.items():
    body = re.sub(r"%.*", "", txt)
    body = re.sub(r"\\(?:label|ref|eqref|gls|glsentryshort|cite\w*)\{[^}]*\}", "", body)
    for sym, label in ((";", "point-virgule"), ("---", "tiret cadratin")):
        n = body.count(sym)
        if n:
            problems.append("%d %s restant(s) dans %s" % (n, label, f))
    # deux-points hors URL, hors YAML de l'exemple de registre, hors ratio
    for line in body.splitlines():
        if ":" in line and "http" not in line and "name:" not in line \
                and "args:" not in line and "label:" not in line \
                and "indicator:" not in line and "sense:" not in line \
                and "threshold:" not in line and "enable:" not in line:
            problems.append("deux-points dans %s : %s" % (f, line.strip()[:90]))

print("\n".join(problems) if problems else "aucun probleme detecte")
