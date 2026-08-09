"""Audit une allocation passee comme graine d'un run a venir, SANS resoudre.

POURQUOI. `run_scenarios.py` audite deja chaque graine avant de l'utiliser, mais il le fait
au moment ou le batch tourne : on apprend que la graine est rejetee apres avoir engage la
machine, et on repart a froid. Quand un run a deja echoue faute d'incumbent -- HiGHS rendant
`maxTimeLimit and no loadable solution` apres deux heures -- la question « une graine
existante serait-elle acceptee, et sinon quelles contraintes la refusent » se pose AVANT de
payer la seconde tentative. Ce script y repond en une minute et sans solve.

CE QU'IL FAIT. Il construit le modele exactement comme le batch le construirait (memes
overrides de scenario, meme dataset), y ecrit l'allocation de chaque graine candidate, puis
evalue toutes les contraintes actives. Une graine est utilisable si et seulement si la liste
des violations est vide -- c'est la definition que `core/solve/warm_start.py` applique, et le
point est qu'HiGHS jette une MIP start infaisable EN SILENCE : sans cet audit, un run parait
chaud et se comporte a froid.

    .venv/Scripts/python scripts/audit_warm_start_seed.py \
        --scenarios case_studies/guadeloupe/plan_etape_A.yaml \
        --run P10_bifurcation_agroecologique \
        --seed outputs/p8_transition_agroecologique_f0_nominal \
        --seed outputs/pareto_azote_threshold_1158542

Sortie : par graine, le nombre de parcelles reprises, celles que le masque d'eligibilite du
nouveau run ecarte, et les contraintes violees avec l'ampleur. Le verdict est binaire ; le
detail sert a savoir s'il manque une reparation ou si la graine est hors sujet.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.case_study import add_argument, load
from core.config import apply_overrides, compose_runs, load_batch_spec, load_config
from core.reporting.run_folder import read_allocation
from core.solve.warm_start import apply_allocation, constraint_violations

# Au-dela, la liste cesse d'informer : on veut savoir QUELLES familles de contraintes
# bloquent, pas enumerer 4 000 contraintes par exploitation.
_MAX_SHOWN = 20


def _select_run(runs: list[dict], wanted: str) -> dict:
    """Le run du spec dont le nom contient `wanted`, en exigeant l'unicite.

    On matche sur une sous-chaine et non sur l'egalite : les noms composes portent leurs
    coordonnees (`P8__F9__pareto_azote__threshold=...`) et personne ne veut les retaper.
    """
    matches = [run for run in runs if wanted in (run.get("name") or "")]
    if not matches:
        available = "\n  ".join(sorted(run.get("name") or "?" for run in runs))
        raise SystemExit(f"Aucun run ne correspond a '{wanted}'. Disponibles :\n  {available}")
    if len(matches) > 1:
        found = "\n  ".join(sorted(run.get("name") or "?" for run in matches))
        raise SystemExit(f"'{wanted}' est ambigu, {len(matches)} runs correspondent :\n  {found}")
    return matches[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scenarios", type=Path, required=True, help="Spec de batch")
    parser.add_argument("--run", required=True, help="Nom (ou fragment de nom) du run a auditer")
    parser.add_argument(
        "--seed", type=Path, action="append", required=True,
        help="Dossier de run servant de graine. Repetable : les graines sont testees dans "
             "l'ordre donne, de la plus proche a la plus lointaine.",
    )
    parser.add_argument("--config", type=Path, default=None, help="config.yaml de reference")
    add_argument(parser)
    args = parser.parse_args()

    case = load(args.case_study)
    base_config = load_config(args.config or case.config_path)
    spec = load_batch_spec(args.scenarios, base_config)
    run_spec = _select_run(compose_runs(spec), args.run)

    name = run_spec.get("name")
    print(f"Run audite : {name}")
    coordinates = " ".join(
        f"{key}={run_spec[key]}" for key in ("policy", "forcing", "sweep") if run_spec.get(key)
    )
    if coordinates:
        print(f"Coordonnees : {coordinates}")

    config = apply_overrides(base_config, run_spec)
    config["run_name"] = name
    print("Construction du dataset et du modele...", flush=True)
    dataset = case.build_dataset(config)

    usable = []
    for seed_dir in args.seed:
        print(f"\n--- graine : {seed_dir} ---")
        if not seed_dir.exists():
            print("  dossier absent -> ignoree")
            continue
        allocation = read_allocation(seed_dir)
        if not allocation:
            print("  aucune allocation lisible -> ignoree")
            continue

        # Le modele est reconstruit pour chaque graine : `apply_allocation` ecrit dans
        # `model.Y`, donc deux graines evaluees sur le meme objet se contamineraient.
        model = case.build_model(dataset, config)
        report = apply_allocation(model, allocation)
        print(f"  {len(allocation)} parcelles lues -- {report.summary()}")

        violations = constraint_violations(model)
        if not violations:
            print("  VERDICT : graine UTILISABLE (aucune contrainte violee)")
            usable.append(seed_dir)
            continue

        print(f"  VERDICT : graine REJETEE -- {len(violations)} contrainte(s) violee(s)")
        for constraint_name, amount in violations[:_MAX_SHOWN]:
            print(f"    {constraint_name:<60} {amount:.6g}")
        if len(violations) > _MAX_SHOWN:
            print(f"    ... et {len(violations) - _MAX_SHOWN} autres")

    print()
    if usable:
        print(f"Au moins une graine passe : {usable[0]}")
        print("-> lancer le batch avec --warm-start-from sur ce dossier.")
        return 0
    print("AUCUNE graine ne passe. Lancer le run tel quel repartirait a froid,")
    print("c'est-a-dire reproduirait l'echec. Reparer une graine ou renoncer au run.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
