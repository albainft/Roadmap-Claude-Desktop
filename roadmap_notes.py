#!/usr/bin/env python3
"""roadmap_notes : une feuille de route en index (ROADMAP.md) et en notes Markdown (une par tâche), sans dépendance.

Dossier des notes (notes/) : <ID>.md pour une tâche, themes/Tn.md pour un thème, parque/Pn.md pour un élément parqué,
journal/AAAA-MM.md pour les entrées sans tâche. Chaque note : un en-tête (id, titre, theme, statut, env, tldr, prochaine, maj, fait),
puis « ## Détail » et « ## Historique » (entrées datées, la plus récente en premier).
ROADMAP.md n'est qu'un index : `sync` y recalcule « Prochaine action », « Statut » et la date de mise à jour.

Commandes : new, maj, done, journal, sync, check, index. Options globales : --roadmap FICHIER, --notes DOSSIER
(ou les variables ROADMAP et ROADMAP_NOTES). Les notes peuvent vivre ailleurs (Nextcloud, Obsidian) : il suffit de
pointer --notes vers leur copie locale."""
import argparse
import datetime
import json
import os
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROADMAP = pathlib.Path(os.environ.get("ROADMAP", HERE / "ROADMAP.md"))
NOTES = pathlib.Path(os.environ.get("ROADMAP_NOTES", HERE / "notes"))
ORDER = ("id", "titre", "type", "theme", "statut", "env", "tldr", "prochaine", "maj", "verifie", "fait")
STATUTS = ("fait", "next", "cours", "decision", "wait", "plan", "todo")
ENTRY = re.compile(r"^- (\d{4}-\d\d-\d\d)(?: (\d\d:\d\d))? : (.*)$")


def now():
    return datetime.datetime.now()


def today():
    return now().date().isoformat()


def clip(t, n):
    t = " ".join(str(t).split())
    if len(t) <= n:
        return t
    c = t.rfind(" ", 0, n)
    return t[: c if c > n // 2 else n].rstrip(" ,;:") + "…"


def fmt(v):
    if isinstance(v, list):
        return "[" + ", ".join(str(x) for x in v) + "]"
    return json.dumps("" if v is None else str(v), ensure_ascii=False)


def render(fm, body):
    keys = [k for k in ORDER if k in fm] + [k for k in fm if k not in ORDER]
    return "---\n" + "".join(f"{k}: {fmt(fm[k])}\n" for k in keys) + "---\n\n" + body.strip("\n") + "\n"


def scalar(v):
    v = v.strip()
    if v.startswith('"'):
        try:
            return json.loads(v)
        except ValueError:
            return v.strip('"')
    if v.startswith("["):
        return [x.strip().strip("\"'") for x in v.strip("[]").split(",") if x.strip()]
    return v.strip("'")


def parse(text):
    m = re.match(r"---\n(.*?)\n---\n\n?(.*)", text, re.S)
    if not m:
        return {}, text
    fm = {}
    for line in m.group(1).split("\n"):
        k = re.match(r"^([A-Za-z_]+):\s*(.*)$", line)
        if k:
            fm[k.group(1)] = scalar(k.group(2))
    return fm, m.group(2)


def key_of(i):
    if "/" in i:
        return i
    if re.fullmatch(r"P\d+", i):
        return "parque/" + i
    if re.fullmatch(r"T\d+", i):
        return "themes/" + i
    return i


def path_of(key):
    return NOTES / f"{key}.md"


def load_notes():
    out = {}
    for f in sorted(NOTES.rglob("*.md")):
        key = str(f.relative_to(NOTES))[:-3]
        fm, body = parse(f.read_text(encoding="utf-8"))
        out[key] = {"fm": fm, "body": body}
    return out


def save(key, fm, body):
    p = path_of(key)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(render(fm, body), encoding="utf-8")


def history_lines(body):
    m = re.search(r"## Historique\n(.*?)(?=\n## |\Z)", body, re.S)
    return [l for l in (m.group(1).split("\n") if m else []) if l.startswith("- ")]


def entries():
    out = []
    for key, n in load_notes().items():
        for line in history_lines(n["body"]):
            m = ENTRY.match(line)
            if m:
                out.append({"date": m.group(1), "time": m.group(2) or "", "text": line[2:], "key": key})
    out.sort(key=lambda e: (e["date"], e["time"]), reverse=True)
    return out


def add_history(body, line):
    if "## Historique" in body:
        return re.sub(r"(## Historique\n\n?)", lambda m: m.group(1) + line + "\n", body, count=1)
    return body.rstrip("\n") + f"\n\n## Historique\n\n{line}\n"


def add_detail(body, text):
    if "## Détail" not in body:
        return body.rstrip("\n") + f"\n\n## Détail\n\n{text}\n"
    head, _, tail = body.partition("## Détail")
    m = re.search(r"\n## Historique\n", tail)
    cut = m.start() if m else len(tail)
    return head + "## Détail" + tail[:cut].rstrip("\n") + f"\n\n{text}\n" + tail[cut:]


def line_of(texte):
    return f"- {now():%Y-%m-%d %H:%M} : {texte}"


def read_index(path):
    lines = pathlib.Path(path).read_text(encoding="utf-8").split("\n")
    tasks, themes, parque, section, blocks, cur = [], [], [], "", [], None
    for i, l in enumerate(lines):
        if l.startswith("## "):
            section, cur = l[3:], None
            continue
        m = re.match(r"### (T\d+)\.", l)
        if m:
            cur = {"id": m.group(1), "start": i, "tasks": []}
            blocks.append(cur)
            themes.append(m.group(1))
            continue
        m = re.match(r"- \[([ x])\] ([A-Z]\d+[a-z]?) ", l)
        if m:
            tasks.append((m.group(2), m.group(1) == "x"))
            if cur is not None:
                cur["tasks"].append((m.group(2), m.group(1) == "x"))
        m = re.match(r"- (P\d+) ", l)
        if m and section.startswith("Parqué"):
            parque.append(m.group(1))
    return lines, tasks, themes, parque, blocks, any(l.startswith("## Journal") for l in lines)


def write_index(lines):
    tmp = ROADMAP.with_suffix(".md.tmp")
    tmp.write_text("\n".join(lines), encoding="utf-8")
    os.replace(tmp, ROADMAP)


def cmd_new(a):
    key = key_of(a.id)
    if path_of(key).exists():
        sys.exit(f"roadmap_notes : {a.id} existe déjà")
    fm = {"id": a.id, "titre": a.titre}
    if key.startswith("parque/"):
        fm.update(type="parque", statut="parque")
    elif key.startswith("themes/"):
        fm.update(type="theme", statut="en cours", verifie=today())
    else:
        fm.update(theme=a.theme, statut=a.statut)
    fm.update(env=[x for x in a.env.split(",") if x], tldr=a.tldr, prochaine=a.prochaine, maj=today())
    save(key, fm, f"# {a.id}. {a.titre}\n\n## Détail\n\n{a.detail}\n\n## Historique\n\n{line_of(f'{a.id} ajoutée : {a.titre}')}\n")
    lines, _t, _th, _p, blocks, _j = read_index(ROADMAP)
    if key.startswith("parque/"):
        at = next((i for i, l in enumerate(lines) if l.startswith("## Parqué")), None)
        if at is not None:
            end = next((i for i in range(at + 1, len(lines)) if lines[i].startswith("## ")), len(lines))
            last = max([i for i in range(at + 1, end) if lines[i].startswith("- P")] or [at])
            lines.insert(last + 1, f"- {a.id} {a.titre}")
            write_index(lines)
    elif not key.startswith("themes/") and a.theme:
        b = next((b for b in blocks if b["id"] == a.theme), None)
        if b is None:
            sys.exit(f"roadmap_notes : thème {a.theme} absent de {ROADMAP.name} (note créée, ligne à ajouter à la main)")
        end = next((i for i in range(b["start"] + 1, len(lines)) if lines[i].startswith(("## ", "### "))), len(lines))
        at = max([i for i in range(b["start"] + 1, end) if lines[i].startswith("- [ ] ")] or [b["start"]]) + 1
        if at == b["start"] + 1:
            at = max([i for i in range(b["start"] + 1, end) if re.match(r"(Statut|Objectif|Prochaine action|Bloqueur)", lines[i])] or [b["start"]]) + 1
        lines.insert(at, f"- [ ] {a.id} {a.titre}")
        write_index(lines)
    print(f"{a.id} créée")


def cmd_maj(a):
    key = key_of(a.id)
    if not path_of(key).exists():
        sys.exit(f"roadmap_notes : note {a.id} introuvable")
    fm, body = parse(path_of(key).read_text(encoding="utf-8"))
    for kv in a.champs:
        k, _, v = kv.partition("=")
        if k not in ORDER or k in ("id", "maj", "type"):
            sys.exit(f"roadmap_notes : champ non modifiable ou inconnu : {k}")
        if k == "statut" and v not in STATUTS + ("parque", "en cours"):
            sys.exit(f"roadmap_notes : statut inconnu : {v} ({', '.join(STATUTS)})")
        fm[k] = [x.strip() for x in v.strip("[]").split(",") if x.strip()] if k == "env" else v
    if a.ajout:
        body = add_detail(body, a.ajout)
    if a.journal:
        body = add_history(body, line_of(a.journal))
    fm["maj"] = today()
    save(key, fm, body)
    print(f"{a.id} mise à jour")


def cmd_done(a):
    lines, tasks, _th, _p, blocks, _j = read_index(ROADMAP)
    i = next((i for i, l in enumerate(lines) if re.match(rf"- \[ \] {re.escape(a.id)} ", l)), None)
    if i is None:
        sys.exit(f"roadmap_notes : {a.id} n'est pas une tâche ouverte de {ROADMAP.name}")
    line = lines.pop(i).replace("- [ ]", "- [x]", 1)
    avant = [b for b in blocks if b["start"] < i]
    if not avant:
        sys.exit(f"roadmap_notes : {a.id} n'est sous aucun thème (### Tn.) de {ROADMAP.name}")
    b = avant[-1]
    end = next((j for j in range(b["start"] + 1, len(lines)) if lines[j].startswith(("## ", "### "))), len(lines))
    last_task = max([j for j in range(b["start"] + 1, end) if lines[j].startswith(("- [ ] ", "- [x] "))] or [b["start"]])
    lines.insert(last_task + 1, line)
    write_index(lines)
    cmd_maj(argparse.Namespace(id=a.id, champs=["statut=fait", f"fait={today()}", "prochaine="], ajout=None, journal=f"{a.id} : {a.resume}"))


def cmd_journal(a):
    if a.texte:
        if a.tache:
            key = key_of(a.tache)
            fm, body = parse(path_of(key).read_text(encoding="utf-8"))
            fm["maj"] = today()
            save(key, fm, add_history(body, line_of(a.texte)))
            print(f"entrée ajoutée à {a.tache}")
            return
        key = f"journal/{now():%Y-%m}"
        if path_of(key).exists():
            fm, body = parse(path_of(key).read_text(encoding="utf-8"))
        else:
            name = key.split("/")[1]
            fm, body = {"id": name, "titre": f"Journal général {name}", "type": "journal"}, f"# Journal général {name}\n"
        fm["maj"] = today()
        save(key, fm, add_history(body, line_of(a.texte)))
        print(f"entrée ajoutée à {key}")
        return
    limite = (now().date() - datetime.timedelta(days=a.depuis)).isoformat()
    n = 0
    for e in entries():
        if e["date"] < limite or n >= a.max:
            continue
        print(f"[{e['key']}] {clip(e['text'], a.largeur)}")
        n += 1
    print(f"{n} entrée(s) depuis {limite}", file=sys.stderr)


def wanted_lines(blocks, notes):
    out = {}
    for b in blocks:
        first = next((t for t, done in b["tasks"] if not done), None)
        n = notes.get(first, {}).get("fm", {}) if first else {}
        out[b["id"]] = {"Prochaine action": f"{first} {clip(n.get('prochaine') or n.get('titre') or '', 220)}".strip() if first else "aucune tâche ouverte"}
        t = notes.get("themes/" + b["id"], {}).get("fm", {})
        if t.get("verifie"):
            out[b["id"]]["Statut"] = f"{t.get('statut') or 'en cours'} (vérifié le {t['verifie']})"
    return out


def cmd_sync(a):
    lines, _t, _th, _p, blocks, _j = read_index(ROADMAP)
    want, diffs = wanted_lines(blocks, load_notes()), []
    for b in blocks:
        end = next((i for i in range(b["start"] + 1, len(lines)) if lines[i].startswith(("## ", "### "))), len(lines))
        for field, val in want[b["id"]].items():
            idx = next((i for i in range(b["start"] + 1, end) if lines[i].startswith(field + " :")), None)
            new = f"{field} : {val}"
            if idx is None:
                diffs.append(f"{b['id']} : ligne « {field} » absente")
            elif lines[idx] != new:
                diffs.append(f"{b['id']} : {field} à jour")
                lines[idx] = new
    if a.check:
        print("\n".join(diffs) if diffs else "lignes dérivées à jour")
        sys.exit(1 if diffs else 0)
    for i, l in enumerate(lines):
        if l.startswith("Dernière mise à jour :"):
            lines[i] = f"Dernière mise à jour : {today()}."
    write_index(lines)
    print("\n".join(diffs) if diffs else "lignes dérivées déjà à jour", "; date de mise à jour posée")


def cmd_check(a):
    lines, tasks, themes, parque, blocks, has_journal = read_index(ROADMAP)
    notes, bad = load_notes(), []
    for tid, done in tasks:
        n = notes.get(tid)
        if not n:
            bad.append(f"{tid} : pas de note")
            continue
        fm = n["fm"]
        for k in ("titre", "theme", "statut", "env", "tldr"):
            if not fm.get(k):
                bad.append(f"{tid} : champ {k} vide")
        if fm.get("statut") not in STATUTS:
            bad.append(f"{tid} : statut invalide ({fm.get('statut')})")
        if done and fm.get("statut") != "fait":
            bad.append(f"{tid} : cochée mais statut {fm.get('statut')}")
        if not done and fm.get("statut") == "fait":
            bad.append(f"{tid} : ouverte mais statut fait")
    for t in themes:
        n = notes.get("themes/" + t)
        if not n:
            bad.append(f"{t} : pas de note de thème")
        elif not (n["fm"].get("tldr") and n["fm"].get("verifie")):
            bad.append(f"{t} : tldr ou verifie vide")
    for p in parque:
        n = notes.get("parque/" + p)
        if not n:
            bad.append(f"{p} : pas de note de parqué")
        elif not n["fm"].get("tldr"):
            bad.append(f"{p} : tldr vide")
    known = {t for t, _ in tasks} | {"themes/" + t for t in themes} | {"parque/" + p for p in parque}
    for key in notes:
        if key.split("/")[0] != "journal" and key not in known:
            bad.append(f"{key} : note sans ligne dans {ROADMAP.name}")
    if has_journal:
        bad.append(f"{ROADMAP.name} contient une section « Journal » (le journal vit dans les notes)")
    want = wanted_lines(blocks, notes)
    for b in blocks:
        end = next((i for i in range(b["start"] + 1, len(lines)) if lines[i].startswith(("## ", "### "))), len(lines))
        for field, val in want[b["id"]].items():
            if not any(l == f"{field} : {val}" for l in lines[b["start"]:end]):
                bad.append(f"{b['id']} : « {field} » pas à jour (lancer sync)")
    print("\n".join(bad) if bad else f"{len(tasks)} tâches, {len(themes)} thèmes, {len(parque)} parqués : notes cohérentes")
    sys.exit(1 if bad else 0)


def cmd_index(a):
    for key, n in sorted(load_notes().items()):
        fm = n["fm"]
        print(f"{key:16} {str(fm.get('statut', '?')):8} {str(fm.get('titre', ''))[:64]}")


def main():
    global ROADMAP, NOTES
    ap = argparse.ArgumentParser(prog="roadmap_notes", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--roadmap", default=str(ROADMAP))
    ap.add_argument("--notes", default=str(NOTES))
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("new", help="crée une note de tâche (et sa ligne dans l'index avec --theme), de thème (Tn) ou de parqué (Pn)")
    p.add_argument("id")
    p.add_argument("--theme", default="")
    p.add_argument("--titre", required=True)
    p.add_argument("--tldr", default="")
    p.add_argument("--prochaine", default="")
    p.add_argument("--statut", default="todo", choices=STATUTS)
    p.add_argument("--env", default="")
    p.add_argument("--detail", default="")
    p.set_defaults(fn=cmd_new)
    p = sub.add_parser("maj", help="modifie une note : maj A3 statut=cours prochaine='…' [--journal '…'] [--ajout '…']")
    p.add_argument("id")
    p.add_argument("champs", nargs="*")
    p.add_argument("--journal", help="entrée datée ajoutée à l'historique de la note")
    p.add_argument("--ajout", help="paragraphe ajouté à la fin du détail")
    p.set_defaults(fn=cmd_maj)
    p = sub.add_parser("done", help="coche la tâche, la range après les ouvertes, passe sa note à fait et journalise")
    p.add_argument("id")
    p.add_argument("resume", help="ce qui a été fait, en une phrase")
    p.set_defaults(fn=cmd_done)
    p = sub.add_parser("journal", help="sans texte : liste les entrées récentes ; avec texte : ajoute une entrée datée")
    p.add_argument("texte", nargs="?")
    p.add_argument("--tache", help="note qui reçoit l'entrée (sinon le journal général du mois)")
    p.add_argument("--depuis", type=int, default=7)
    p.add_argument("--max", type=int, default=40)
    p.add_argument("--largeur", type=int, default=240)
    p.set_defaults(fn=cmd_journal)
    p = sub.add_parser("sync", help="recalcule « Prochaine action », « Statut » de chaque thème et la date de mise à jour")
    p.add_argument("--check", action="store_true")
    p.set_defaults(fn=cmd_sync)
    sub.add_parser("check", help="compare l'index et les notes").set_defaults(fn=cmd_check)
    sub.add_parser("index", help="liste les notes").set_defaults(fn=cmd_index)
    a = ap.parse_args()
    ROADMAP, NOTES = pathlib.Path(a.roadmap), pathlib.Path(a.notes)
    a.fn(a)


if __name__ == "__main__":
    main()
