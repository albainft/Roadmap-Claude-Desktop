#!/usr/bin/env python3
"""Génère ROADMAP.html et ROADMAP.artifact.html depuis ROADMAP.md : thèmes, tâches avec statut et environnement, filtres, tri, journal.

Usage : python3 gen_roadmap_html.py [ROADMAP.md [sortie.html]] [--notes=DOSSIER] [--notes-url=URL/] [--launch="/commande {id}"]
Écrit la page complète et, à côté, ROADMAP.artifact.html (contenu seul, pour un artefact Claude Desktop). Avec --launch,
chaque tâche ouverte reçoit un bouton « Lancer » qui envoie la commande (l'artefact doit déclarer la capacité `comments`).
Notes : si un dossier notes/ existe à côté de ROADMAP.md (ou --notes), chaque tâche prend son titre, son statut, ses environnements,
son TL;DR, sa prochaine étape et son historique dans sa note (roadmap_notes.py), et le journal est reconstitué depuis les historiques ;
--notes-url=URL/ ajoute un bouton « Ouvrir » vers URL/<ID>.md. Sans note, statuts et environnements sont déduits du texte des tâches.
Balises : des [mots] en tête de ligne d'une tâche deviennent des pastilles (« [✓plan] » en vert, « [plan:⏳] » en gris).
Rien n'est écrit dans le Markdown."""
import html
import os
import json
import pathlib
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import roadmap_notes as rn

ARGS = [x for x in sys.argv[1:] if not x.startswith("--")]
LAUNCH = next((x.split("=", 1)[1] for x in sys.argv[1:] if x.startswith("--launch=")), None)
NOTES_DIR = next((x.split("=", 1)[1] for x in sys.argv[1:] if x.startswith("--notes=")), None)
NOTES_URL = next((x.split("=", 1)[1] for x in sys.argv[1:] if x.startswith("--notes-url=")), "")
SRC = pathlib.Path(ARGS[0] if ARGS else "ROADMAP.md")
OUT = pathlib.Path(ARGS[1] if len(ARGS) > 1 else str(SRC.with_suffix(".html")))
FIELDS = ("Statut", "Objectif", "Fait", "Briques existantes", "Prochaine action", "Bloqueur")
NOTES = {}
_nd = pathlib.Path(NOTES_DIR) if NOTES_DIR else SRC.parent / "notes"
if _nd.is_dir():
    rn.NOTES = _nd
    NOTES = rn.load_notes()

ENVS = [
    ("secu", "Sécurité", r"sécurité|secret|mot de passe|authentification|chiffrement|droits|permission"),
    ("infra", "Infra et déploiement", r"déploiement|deploy|docker|serveur|hébergement|domaine|pipeline|\bci\b|monitoring"),
    ("code", "Code et dépôts", r"dépôt|git|branche|commit|revue de code|refactor|test"),
    ("auto", "Automatisation", r"automatis|script|robot|planifi|cron|tâche récurrente"),
    ("comm", "Communication", r"notification|e-mail|mail|message|annonce|newsletter"),
    ("data", "Données", r"base de données|données|migration|import|export|sauvegarde|stockage"),
    ("prod", "Produit", r"fonctionnalité|écran|interface|parcours|utilisateur|page|design"),
    ("ops", "Exploitation", r"support|incident|maintenance|exploitation|documentation|guide"),
]
ENV_NAMES = {k: n for k, n, _ in ENVS}

STATUS = {
    "fait": ("Fait", "ok"),
    "next": ("Prochaine action", "nx"),
    "cours": ("En cours", "ec"),
    "decision": ("Attente décision", "td"),
    "wait": ("En attente", "lt"),
    "plan": ("Planifié", "pl"),
    "todo": ("À faire", "tt"),
}
OVERRIDES = {}


def inline(t):
    t = html.escape(t, quote=False)
    t = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r'<a href="\2">\1</a>', t)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    t = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", t)
    return t


def split_title(text):
    m = re.search(r" : ", text)
    if m and m.start() <= 170:
        return text[:m.start()], text[m.end():]
    if len(text) <= 150:
        return text, ""
    cut = text.rfind(" ", 0, 140)
    return text[:cut] + "…", text


def envs_of(text):
    low = text.lower()
    return [k for k, _, rx in ENVS if re.search(rx, low)][:3]


def status_of(tid, text, done, first):
    if done:
        return "fait", ""
    if tid in OVERRIDES:
        return OVERRIDES[tid]
    low = text.lower()
    if re.search(r"sur confirmation|plan à valider|à valider|décision en attente|attente de (la )?validation", low) and first:
        return "decision", ""
    if first:
        return "next", ""
    if re.search(r"à partir du 20\d\d-\d\d-\d\d", low):
        return "plan", ""
    if re.search(r"(?:fait|faite|faits|faites|traitées?|préparé)[^.;]{0,40} le 20\d\d-\d\d-\d\d", low):
        return "cours", ""
    if re.search(r"attend l|attend la|attend le|attend les|en attente d|dépend de|après r\d|après les renommages", low):
        return "wait", ""
    return "todo", ""


def env_chips(keys):
    return "".join(f'<span class="env e-{k}">{ENV_NAMES[k]}</span>' for k in keys)


def pill(code, extra=""):
    label, cls = STATUS[code]
    return f'<span class="pill {cls}">{label}{(" : " + html.escape(extra)) if extra else ""}</span>'


def cell_html(c, col_is_status=False):
    low = c.lower()
    if col_is_status:
        if re.match(r"(fait|publié)", low):
            return f'<span class="pill ok">{inline(c)}</span>'
        if re.match(r"(à faire|plan à valider|\d+ (non|modif)|branche|publié, défaut)", low):
            return f'<span class="pill td">{inline(c)}</span>'
        if re.match(r"(après|avec|attend)", low):
            return f'<span class="pill lt">{inline(c)}</span>'
    return inline(c)


def table(rows):
    cells = [[c.strip() for c in r.strip().strip("|").split("|")] for r in rows]
    head, body = cells[0], cells[2:]
    status_cols = {i for i, h in enumerate(head) if h.lower().startswith("statut")}
    h = "".join(f"<th>{inline(c)}</th>" for c in head)
    b = ""
    for r in body:
        tds = ""
        for i, c in enumerate(r):
            cls = ""
            tds += f'<td class="{cls}">{cell_html(c, i in status_cols or (i == 1 and head[1].lower() == "statut"))}</td>'
        b += f"<tr>{tds}</tr>"
    return f"<table><thead><tr>{h}</tr></thead><tbody>{b}</tbody></table>"


def note_code(fm, done, first):
    code = "fait" if done else str(fm.get("statut") or "todo")
    if code not in STATUS:
        code = "todo"
    if not done and first:
        return "decision" if code == "decision" else "next"
    if not done and code == "next":
        return "todo"
    return code


TICK = "✓"
BALISES_TETE = re.compile(r"^((?:\[[^\]\n]+\](?!\()\s*)+)")


def balises_html(text):
    m = BALISES_TETE.match(text)
    if not m:
        return text, ""
    puces = []
    for p in re.findall(r"\[([^\]]+)\]", m.group(1)):
        if p.startswith(TICK) or p.endswith(":" + TICK):
            puces.append(f'<span class="pill ok">{TICK} {html.escape(p.strip(TICK + ":"))}</span>')
        elif p.endswith(":⏳"):
            puces.append(f'<span class="pill lt">… {html.escape(p[:-2])}</span>')
        else:
            puces.append(f'<span class="pill pl">{html.escape(p)}</span>')
    return text[m.end():], "".join(puces)


def task_html(tid, text, done, first, th=0):
    text, bal = balises_html(text)
    note = NOTES.get(tid)
    if note:
        fm = note["fm"]
        title, rest = fm.get("titre") or split_title(text)[0], fm.get("tldr") or ""
        ev = [e for e in (fm.get("env") or []) if e in ENV_NAMES][:3] or ["ops"]
        code, extra = note_code(fm, done, first), ""
        hist = [h[2:] for h in rn.history_lines(note["body"])]
        step = "" if done else (fm.get("prochaine") or "")
        date = f"fait le {fm.get('fait')}" if done and fm.get("fait") else (f"mis à jour le {fm.get('maj')}" if fm.get("maj") else "")
        link = (f'<a class="open" href="{html.escape(NOTES_URL + tid + ".md")}" target="_blank" rel="noopener noreferrer">Ouvrir la note</a>' if NOTES_URL else "")
    else:
        title, rest = split_title(text)
        code, extra = status_of(tid, text, done, first)
        ev = envs_of(text) or ["ops"]
        hist = [j for j in journal if re.match(r"\d{4}-\d\d-\d\d : " + re.escape(tid) + r"\b", j)]
        step, date, link = "", "", ""
    cls = f"task b-{ev[0]}" + (" done" if done else "") + (" next" if code in ("next", "decision") else "")
    meta = ""
    if step or date or link:
        meta = "<p class='meta'>" + (f"<b>Prochaine étape</b> : {inline(step)} " if step else "") + (f"&middot; <span class='small'>{html.escape(date)}</span> " if date else "") + link + "</p>"
    hist_html = ("<p class='lbl'>Historique (" + str(len(hist)) + ")</p><ul class='hist'>" + "".join(f"<li>{inline(j)}</li>" for j in hist) + "</ul>") if hist else ""
    det = f"<details><summary>Détail</summary><p>{inline(rest)}</p>{meta}{hist_html}</details>" if (rest or hist or meta) else ""
    return (f'<article class="{cls}" data-id="{html.escape(tid)}" data-st="{code}" data-env="{" ".join(ev)}" data-th="{th}"><div class="row"><span class="id">{html.escape(tid)}</span><span class="ttl">{inline(title)}</span>'
            f'<span class="tags">{bal}{env_chips(ev)}{pill(code, extra)}</span></div>{det}</article>')


lines = SRC.read_text(encoding="utf-8").split("\n")
title = next((l[2:] for l in lines if l.startswith("# ")), "Feuille de route")
updated = next((l for l in lines if l.startswith("Dernière mise à jour")), "")
themes, verif, parque, journal, suivi = [], [], [], [], []
verif_title, section, cur = "", "", None
for line in lines:
    if line.startswith("## "):
        section = line[3:].strip()
        if section.startswith("Vérifications"):
            verif_title = section
        cur = None
        continue
    if line.startswith("### T"):
        cur = {"title": line[4:].strip(), "fields": {}, "tasks": []}
        themes.append(cur)
        continue
    if section.startswith("Suivi"):
        suivi.append(line)
        continue
    m = re.match(r"- \[([ x])\] (\S+) (.*)", line)
    if m and section.startswith("Thèmes") and cur is not None:
        cur["tasks"].append((m.group(2), m.group(3), m.group(1) == "x"))
    elif m and section.startswith("Vérifications"):
        verif.append((m.group(2), m.group(3), m.group(1) == "x"))
    elif section.startswith("Thèmes") and cur is not None:
        for f in FIELDS:
            if line.startswith(f + " :"):
                cur["fields"][f] = line[len(f) + 2:].strip()
    elif section.startswith("Parqué") and line.startswith("- "):
        parque.append(line[2:])
    elif section.startswith("Journal") and line.startswith("- "):
        journal.append(line[2:])

if NOTES:
    journal = [e["text"] for e in rn.entries()]

suivi_html, buf = [], []
for l in suivi + [""]:
    if l.startswith("|"):
        buf.append(l)
        continue
    if buf:
        suivi_html.append(table(buf))
        buf = []
    if l.strip():
        suivi_html.append(f"<p class='note'>{inline(l.strip())}</p>")

counts = {k: 0 for k in STATUS}
for t in themes:
    seen = False
    for tid, text, done in t["tasks"]:
        code = note_code(NOTES[tid]["fm"], done, not seen and not done) if tid in NOTES else status_of(tid, text, done, not seen and not done)[0]
        counts[code] += 1
        seen = seen or not done
open_total = sum(1 for t in themes for x in t["tasks"] if not x[2])

cards = ""
for i, t in enumerate(themes, 1):
    n = sum(1 for x in t["tasks"] if not x[2])
    nf = len(t["tasks"]) - n
    cards += (f'<a class="card" href="#t{i}"><div class="chead"><b>{inline(t["title"].split(". ", 1)[0])}</b>'
              f'<span class="badge">{nf}/{len(t["tasks"])} faites, {n} ouverte(s)</span></div><div class="ctitle">{inline(t["title"].split(". ", 1)[-1])}</div>'
              f'<div class="lbl">Prochaine action</div><div>{inline(t["fields"].get("Prochaine action", "").replace("Prochaine action : ", ""))}</div>'
              f'<div class="lbl">Bloqueur</div><div class="small">{inline(t["fields"].get("Bloqueur", "").replace("Bloqueur : ", ""))}</div></a>')

stats = "".join(f'<div class="stat"><div class="n">{counts[k]}</div>{pill(k)}</div>' for k in ("next", "cours", "decision", "todo", "wait", "plan", "fait"))
legend_env = "".join(f'<span class="env e-{k}">{n}</span>' for k, n, _ in ENVS)
legend_st = "".join(pill(k) for k in STATUS)

body = ""
for i, t in enumerate(themes, 1):
    dl = "".join(f"<dt>{f}</dt><dd>{inline(t['fields'][f])}</dd>" for f in ("Statut", "Objectif", "Fait", "Briques existantes") if f in t["fields"])
    seen, tasks, fait = False, "", ""
    for tid, text, done in t["tasks"]:
        h = task_html(tid, text, done, not seen and not done, i)
        seen = seen or not done
        if done:
            fait += h
        else:
            tasks += h
    nd = sum(1 for x in t["tasks"] if x[2])
    if fait:
        tasks += f'<details class="doneblock"><summary>Fait ({nd} sur {len(t["tasks"])})</summary>{fait}</details>'
    body += f'<section id="t{i}"><h2>{inline(t["title"])}</h2><dl>{dl}</dl><div class="tasks">{tasks}</div></section>'

verif_html = "".join(task_html(a, b, c, False) for a, b, c in verif)
def parque_item(p):
    m = re.match(r"(P\d+) (.*)", p)
    n = NOTES.get("parque/" + m.group(1)) if m else None
    if not n:
        return f"<li>{inline(p)}</li>"
    fm = n["fm"]
    more = (f" {inline(fm['tldr'])}" if fm.get("tldr") else "") + (f" <span class='small'>Pour reprendre : {inline(fm['prochaine'])}</span>" if fm.get("prochaine") else "")
    return f"<li><b>{html.escape(m.group(1))}</b> {inline(fm.get('titre') or m.group(2))}.{more}</li>"


parque_html = "".join(parque_item(p) for p in parque)
j_vis = "".join(f"<li>{inline(j)}</li>" for j in journal[:8])
j_rest = "".join(f"<li>{inline(j)}</li>" for j in journal[8:])

palette_l = {"secu": ("#534ab7", "#eeedfe"), "infra": ("#0f6e56", "#e1f5ee"), "code": ("#993c1d", "#faece7"), "auto": ("#993556", "#fbeaf0"),
             "comm": ("#185fa5", "#e6f1fb"), "data": ("#3b6d11", "#eaf3de"), "prod": ("#854f0b", "#faeeda"), "ops": ("#5f5e5a", "#f1efe8")}
palette_d = {"secu": ("#afa9ec", "#3c3489"), "infra": ("#5dcaa5", "#085041"), "code": ("#f0997b", "#712b13"), "auto": ("#ed93b1", "#72243e"),
             "comm": ("#85b7eb", "#0c447c"), "data": ("#97c459", "#27500a"), "prod": ("#ef9f27", "#633806"), "ops": ("#b4b2a9", "#444441")}
vars_l = "".join(f"--{k}:{a};--{k}bg:{b};" for k, (a, b) in palette_l.items())
vars_d = "".join(f"--{k}:{a};--{k}bg:{b};" for k, (a, b) in palette_d.items())
env_css = "".join(
    f".e-{k}{{color:var(--{k});background:var(--{k}bg);border:1px solid var(--{k})}}.b-{k}{{border-left:6px solid var(--{k})}}.e-{k}-b{{border-left:5px solid var(--{k});padding-left:10px}}"
    for k, _, _ in ENVS)

css = (":root{--bg:#fff;--fg:#1f1f1c;--mut:#6b6a63;--line:#e3e1d8;--card:#f6f5f0;--acc:#185fa5;--accbg:#e6f1fb;--ok:#27500a;--okbg:#c0dd97;--td:#633806;--tdbg:#fac775;--ltc:#444441;--ltbg:#d3d1c7;--plc:#3c3489;--plbg:#cecbf6;--nxc:#fff;--nxbg:#185fa5;" + vars_l + "}"
       "@media (prefers-color-scheme:dark){:root{--bg:#1c1c1a;--fg:#ecebe5;--mut:#a3a29a;--line:#3a3a36;--card:#262624;--acc:#85b7eb;--accbg:#0c447c;--ok:#c0dd97;--okbg:#27500a;--td:#fac775;--tdbg:#633806;--ltc:#d3d1c7;--ltbg:#444441;--plc:#cecbf6;--plbg:#3c3489;--nxc:#042c53;--nxbg:#85b7eb;" + vars_d + "}}"
       """
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}
main{max-width:1040px;margin:0 auto;padding:24px 20px 80px}h1{font-size:24px;font-weight:500;margin:0}h2{font-size:19px;font-weight:500;margin:36px 0 10px;border-bottom:1px solid var(--line);padding-bottom:6px}
.sub{color:var(--mut);font-size:13px;margin:4px 0 16px}nav{display:flex;flex-wrap:wrap;gap:8px;margin:12px 0 20px}nav a{font-size:13px;padding:4px 12px;border:1px solid var(--line);border-radius:999px;color:var(--fg);text-decoration:none}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px}.card{display:block;background:var(--card);border-radius:10px;padding:14px 16px;color:var(--fg);text-decoration:none;border:1px solid var(--line)}
.chead{display:flex;justify-content:space-between;align-items:center}.badge{font-size:12px;background:var(--accbg);color:var(--acc);padding:2px 10px;border-radius:999px}.ctitle{font-size:14px;color:var(--mut);margin:2px 0 8px}
.lbl{font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);margin-top:8px}.small{font-size:13px;color:var(--mut)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:10px;margin:14px 0}.stat{background:var(--card);border-radius:10px;padding:10px 12px;border:1px solid var(--line)}.n{font-size:26px;font-weight:500;line-height:1.1;margin-bottom:6px}
.legend{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin:10px 0 4px;font-size:13px}.legend div{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin:4px 0}.legend b{font-weight:500;color:var(--mut);min-width:110px}
dl{display:grid;grid-template-columns:130px 1fr;gap:6px 14px;font-size:14px;margin:0 0 14px}dt{color:var(--mut)}dd{margin:0}
.task{border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin:8px 0;background:var(--card)}.task.next{outline:2px solid var(--nxbg)}.task.done{opacity:.6}
.row{display:flex;gap:10px;align-items:baseline;flex-wrap:wrap}.id{font:600 12px ui-monospace,monospace;background:var(--accbg);color:var(--acc);padding:2px 8px;border-radius:6px}.ttl{font-weight:500;flex:1;min-width:200px}
.tags{display:flex;gap:5px;flex-wrap:wrap;margin-left:auto}.env{font-size:11px;padding:1px 8px;border-radius:999px;white-space:nowrap}
.pill{font-size:12px;padding:2px 10px;border-radius:6px;white-space:nowrap;display:inline-block}.ok{background:var(--okbg);color:var(--ok)}.td{background:var(--tdbg);color:var(--td)}.lt{background:var(--ltbg);color:var(--ltc)}.pl{background:var(--plbg);color:var(--plc)}.nx{background:var(--nxbg);color:var(--nxc);font-weight:500}.tt{background:transparent;color:var(--mut);border:1px solid var(--line)}
details{margin-top:6px}summary{cursor:pointer;color:var(--acc);font-size:13px}details p{margin:8px 0 2px;font-size:14px;color:var(--fg);overflow-wrap:anywhere}
code{font:12.5px ui-monospace,monospace;background:var(--accbg);color:var(--fg);padding:1px 5px;border-radius:4px;overflow-wrap:anywhere}a{color:var(--acc)}
table{border-collapse:collapse;width:100%;font-size:13.5px;margin:10px 0 18px}th,td{border-bottom:1px solid var(--line);padding:7px 8px;text-align:left;vertical-align:top}th{color:var(--mut);font-weight:500;font-size:12px;text-transform:uppercase;letter-spacing:.03em}
ul{padding-left:18px}li{margin:6px 0;font-size:14px;overflow-wrap:anywhere}.note{color:var(--mut);font-size:13px}
.open{font-size:12px;text-decoration:none;border:1px solid var(--line);border-radius:6px;padding:1px 8px;color:var(--acc)}.meta{font-size:13px;color:var(--mut)}
.pill.ec{background:var(--accbg);color:var(--acc);border:1px solid var(--acc)}.hist{margin:4px 0 8px;padding-left:18px}.hist li{font-size:13px;color:var(--mut)}.doneblock{margin-top:12px}.doneblock>summary{font-size:14px;color:var(--mut)}
""" + env_css)

budget_line = ""

doc = f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{html.escape(title)}</title><style>{css}</style></head><body><main>
<h1>{html.escape(title)}</h1><div class="sub">{html.escape(updated)} Généré depuis {SRC.name}{" et notes/" if NOTES else ""} : ne pas éditer ce fichier.{budget_line}</div>
<nav><a href="#themes">Thèmes</a><a href="#verif">Vérifications</a><a href="#parque">Parqué</a><a href="#journal">Journal</a></nav>
<div class="legend"><div><b>Statuts</b>{legend_st}</div><div><b>Environnements</b>{legend_env}</div></div>
<section id="themes"><h2>Thèmes actifs ({len(themes)}) et {open_total} tâches ouvertes</h2><div class="stats">{stats}</div><div class="cards">{cards}</div></section>
{body}
<section id="verif"><h2>{html.escape(verif_title)}</h2>{verif_html}</section>
<section id="parque"><h2>Parqué ({len(parque)})</h2><ul>{parque_html}</ul></section>
<section id="journal"><h2>Journal</h2><ul>{j_vis}</ul><details><summary>Entrées plus anciennes ({len(journal) - 8})</summary><ul>{j_rest}</ul></details></section>
</main></body></html>"""
OUT.write_text(doc, encoding="utf-8")
_style = re.search(r"<style>(.*?)</style>", doc, re.S).group(1)
_style = re.sub(r"@media \(prefers-color-scheme:dark\)\{:root\{(.*?)\}\}",
                lambda m: '@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){' + m.group(1) + 'color-scheme:dark}}'
                          ':root[data-theme="dark"]{' + m.group(1) + 'color-scheme:dark}', _style, count=1, flags=re.S)
_body = re.search(r"<body>(.*)</body>", doc, re.S).group(1)
_chips_st = "".join(f'<button type="button" class="chip2 pill {cls}" data-v="{k}" aria-pressed="false">{lab}</button>' for k, (lab, cls) in STATUS.items())
_chips_env = "".join(f'<button type="button" class="chip2 env e-{k}" data-v="{k}" aria-pressed="false">{n}</button>' for k, n, _ in ENVS)
_chips_th = "".join(f'<button type="button" class="chip2 pill lt" data-v="{i}" aria-pressed="false">{html.escape(t["title"].split(". ", 1)[0])}</button>' for i, t in enumerate(themes, 1))
_tools = (
    '<div class="tools" id="tools"><div class="trow"><input id="rq" type="search" placeholder="Rechercher une tâche…" aria-label="Rechercher une tâche">'
    '<select id="rs" aria-label="Trier par"><option value="file">Ordre du fichier</option><option value="st">Tri : statut</option>'
    '<option value="id">Tri : identifiant</option><option value="env">Tri : environnement</option></select></div>'
    '<div class="trow"><button type="button" class="tb" id="rflat" aria-pressed="false">Liste à plat</button>'
    '<button type="button" class="tb" id="rdone" aria-pressed="false">Masquer les faites</button>'
    '<button type="button" class="tb" id="rexp">Tout déplier</button><button type="button" class="tb" id="rrst">Réinitialiser</button>'
    '<span class="small" id="rcount"></span></div>'
    '<details><summary>Filtres : statut, environnement, thème</summary>'
    f'<div class="tgrp"><span class="small">Statut</span>{_chips_st}</div>'
    f'<div class="tgrp"><span class="small">Environnement</span>{_chips_env}</div>'
    f'<div class="tgrp"><span class="small">Thème</span>{_chips_th}</div></details></div>')
_tcss = (".tools{margin:16px 0;padding:10px 14px;border:1px solid var(--line);border-radius:10px;background:var(--card)}"
         ".tools>summary{cursor:pointer;font-weight:500}.tools input,.tools select{font:inherit;padding:6px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg)}"
         ".tools input{width:100%;margin:10px 0 4px}.tgrp{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:8px}"
         ".chip2{cursor:pointer;font:inherit;font-size:12px;opacity:.5;border:1px solid transparent;border-radius:999px}.chip2.pill{border-radius:6px}"
         ".chip2[aria-pressed=\"true\"]{opacity:1;outline:2px solid var(--fg);outline-offset:1px}"
         ".tb{font:inherit;font-size:13px;padding:4px 10px;border:1px solid var(--line);border-radius:8px;background:var(--bg);color:var(--fg);cursor:pointer}"
         ".tb[aria-pressed=\"true\"]{background:var(--accbg);color:var(--acc);border-color:var(--acc)}"
         ".chip2:focus-visible,.tb:focus-visible,.tools input:focus-visible,.tools select:focus-visible{outline:2px solid var(--acc);outline-offset:2px}"
         "#flat .task{margin:6px 0}[hidden]{display:none!important}"
         "main{padding:10px 14px 40px}h1{font-size:19px}.sub{margin:2px 0 6px;font-size:12px}h2{font-size:16px;margin:16px 0 6px}"
         "nav{margin:6px 0 8px;gap:6px}nav a{font-size:12px;padding:2px 10px}.legend{display:none}"
         ".stats{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}.stat{display:flex;align-items:center;gap:6px;padding:2px 10px 2px 8px;border-radius:999px}.stat .n{font-size:14px;font-weight:600}"
         ".cards{grid-template-columns:1fr;gap:6px}.card{padding:8px 12px}.card .lbl,.card .small{display:none}.ctitle{font-size:13px;margin:2px 0}"
         ".card>div:not(.chead):not(.ctitle):not(.lbl):not(.small){font-size:13px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}"
         "dl{font-size:13px;margin:0 0 8px}dt:nth-of-type(n+3),dd:nth-of-type(n+3){display:none}"
         ".task{padding:5px 10px;margin:4px 0}.task .row{gap:8px}.task .tags .env{display:none}.ttl{font-size:13.5px;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}"
         ".task details{margin-top:4px}.tools{padding:8px 10px;margin:10px 0}.tools .trow{display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:6px}.tools .trow:first-child{margin-top:0}"
         ".tools input{flex:1 1 180px;margin:0;width:auto}.tools details{margin-top:8px}.tools summary{font-size:13px;color:var(--acc)}"
         ".go{flex:none;display:inline-flex;align-items:center;gap:4px;border:1px solid var(--line);background:var(--bg);color:var(--acc);border-radius:6px;padding:1px 7px;cursor:pointer;font:inherit;font-size:12px}"
         ".go:hover{border-color:var(--acc)}.go:disabled{opacity:.6;cursor:default}.go:focus-visible{outline:2px solid var(--acc);outline-offset:2px}.gomsg{font-size:12px;color:var(--mut)}"
         "section.fold>details>summary{font-size:16px;font-weight:500;color:var(--fg);padding:6px 0;border-bottom:1px solid var(--line)}section.fold>details{margin-top:14px}table{font-size:12.5px}")
_js = r"""
(function(){
const ORDST=%s, ORDENV=%s, $=s=>document.querySelector(s);
const tasks=[...document.querySelectorAll('article.task')]; tasks.forEach((t,i)=>t.dataset.i=i);
const S={st:new Set(),env:new Set(),th:new Set()}; let hideDone=false, flat=false, sortBy='file';
const flatBox=document.createElement('div'); flatBox.id='flat'; flatBox.hidden=true; $('#tools').after(flatBox);
const idKey=id=>{const m=/^([A-Z]+)(\d+)/.exec(id)||[0,id,0]; return [m[1],+m[2]];};
const cmp={file:(a,b)=>a.dataset.i-b.dataset.i,
 st:(a,b)=>ORDST.indexOf(a.dataset.st)-ORDST.indexOf(b.dataset.st)||a.dataset.i-b.dataset.i,
 id:(a,b)=>{const x=idKey(a.dataset.id),y=idKey(b.dataset.id); return x[0]<y[0]?-1:x[0]>y[0]?1:x[1]-y[1];},
 env:(a,b)=>ORDENV.indexOf((a.dataset.env||'ops').split(' ')[0])-ORDENV.indexOf((b.dataset.env||'ops').split(' ')[0])||a.dataset.i-b.dataset.i};
const norm=s=>s.normalize('NFD').replace(/[\u0300-\u036f]/g,'').toLowerCase();
function ok(t,q){
 if(hideDone&&t.dataset.st==='fait')return false;
 if(S.st.size&&!S.st.has(t.dataset.st))return false;
 if(S.th.size&&!S.th.has(t.dataset.th))return false;
 if(S.env.size&&![...S.env].some(e=>(t.dataset.env||'').split(' ').includes(e)))return false;
 return !q||norm(t.textContent).includes(q);}
var apply=function(){
 const q=norm($('#rq').value.trim()), vis=tasks.filter(t=>ok(t,q)), c=cmp[sortBy];
 tasks.forEach(t=>t.hidden=!vis.includes(t));
 document.querySelectorAll('.tasks').forEach(box=>{
  const db=box.querySelector(':scope > details.doneblock');
  [...box.querySelectorAll(':scope > article.task')].sort(c).forEach(t=>box.insertBefore(t,db));
  if(db)[...db.querySelectorAll('article.task')].sort(c).forEach(t=>db.appendChild(t));
  box.hidden=flat;});
 flatBox.replaceChildren(...(flat?[...vis].sort(c).map(t=>{const x=t.cloneNode(true); x.hidden=false;
   const tag=document.createElement('span'); tag.className='id'; tag.textContent='T'+t.dataset.th; x.querySelector('.row').prepend(tag); return x;}):[]));
 flatBox.hidden=!flat;
 $('#rcount').textContent=vis.length+' tâche(s) affichée(s) sur '+tasks.length;}
function tog(group,btn){const v=btn.dataset.v,set=S[group]; set.has(v)?set.delete(v):set.add(v); btn.setAttribute('aria-pressed',set.has(v)); apply();}
[['#f-st','st'],['#f-env','env'],['#f-th','th']].forEach(([_,g])=>0);
document.querySelectorAll('.tgrp').forEach(grp=>{const b=grp.querySelector('.chip2'); if(!b)return;
 const g=b.classList.contains('env')?'env':(ORDST.includes(b.dataset.v)?'st':'th');
 grp.querySelectorAll('.chip2').forEach(x=>x.addEventListener('click',()=>tog(g,x)));});
$('#rq').addEventListener('input',apply);
$('#rs').addEventListener('change',e=>{sortBy=e.target.value;apply();});
$('#rflat').addEventListener('click',e=>{flat=!flat;e.currentTarget.setAttribute('aria-pressed',flat);apply();});
$('#rdone').addEventListener('click',e=>{hideDone=!hideDone;e.currentTarget.setAttribute('aria-pressed',hideDone);apply();});
let open=false; $('#rexp').addEventListener('click',e=>{open=!open; document.querySelectorAll('article.task details').forEach(d=>d.open=open); e.currentTarget.textContent=open?'Tout replier':'Tout déplier';});
$('#rrst').addEventListener('click',()=>{S.st.clear();S.env.clear();S.th.clear();hideDone=false;flat=false;sortBy='file';$('#rq').value='';$('#rs').value='file';
 document.querySelectorAll('.chip2,.tb[aria-pressed]').forEach(b=>b.setAttribute('aria-pressed','false'));apply();});

let CM=null; (window.claude&&claude.use?claude.use('comments'):Promise.resolve(null)).then(c=>{CM=c;}).catch(()=>{});
const GO='<svg width="10" height="10" viewBox="0 0 10 10" aria-hidden="true"><path d="M2 1l7 4-7 4z" fill="currentColor"/></svg>Lancer';
function addGo(art){ if(art.dataset.st==='fait'||art.querySelector('.go'))return; const row=art.querySelector('.row'); if(!row)return;
 const b=document.createElement('button'); b.type='button'; b.className='go'; b.innerHTML=GO; b.title="Lancer le traitement de l'étape "+art.dataset.id; b.setAttribute('aria-label',b.title);
 row.prepend(b);}
tasks.forEach(addGo);
const _apply=apply; apply=function(){_apply(); document.querySelectorAll('#flat article.task').forEach(addGo);};
async function copyText(t){ try{ await navigator.clipboard.writeText(t); return true;}catch(e){ return false; } }
document.addEventListener('click',async ev=>{
 const b=ev.target.closest('.go'); if(!b)return; const art=b.closest('article.task'), id=art.dataset.id, text='/ROADMAP go '+id;
 let msg=art.querySelector('.gomsg'); if(!msg){msg=document.createElement('span'); msg.className='gomsg'; b.after(msg);} b.disabled=true; msg.textContent='…';
 try{
  const ok=CM&&(await CM.canSendToClaude())==='available';
  if(ok){ const a=await CM.anchorFor(art); await CM.sendToClaude({anchor:a,text}); msg.textContent='Envoyé à Claude'; }
  else if(await copyText(text)){ msg.textContent='Copié : collez « '+text+' » dans le chat'; }
  else { msg.textContent='À coller dans le chat : '+text; }
 }catch(e){
  msg.textContent=(await copyText(text))?'Copié : collez « '+text+' » dans le chat':'À coller dans le chat : '+text; }
 setTimeout(()=>{b.disabled=false;},2500);});
['suivi','verif','parque','journal'].forEach(id=>{const sec=document.getElementById(id); if(!sec)return; const h=sec.querySelector('h2'); if(!h)return;
 const d=document.createElement('details'), sm=document.createElement('summary'); sm.textContent=h.textContent; h.remove();
 while(sec.firstChild)d.appendChild(sec.firstChild); d.prepend(sm); sec.appendChild(d); sec.classList.add('fold');});
apply();
})();
""" % (json.dumps(list(STATUS)), json.dumps([k for k, _, _ in ENVS] + ["ops"]))
if LAUNCH:
    _js = _js.replace("text='/ROADMAP go '+id", "text=" + json.dumps(LAUNCH) + ".replace('{id}', id)")
else:
    _a, _b = _js.index("let CM=null;"), _js.index("['suivi','verif'")
    _js = _js[:_a] + _js[_b:]
OUT.with_name(OUT.stem + ".artifact.html").write_text(
    f"<title>{html.escape(title)}</title><style>{_style}{_tcss}</style>" + _body.replace('<section id="themes">', _tools + '<section id="themes">', 1) + f"<script>{_js}</script>", encoding="utf-8")
print(f"{OUT} écrit : {len(themes)} thèmes, {open_total} tâches ouvertes ({', '.join(f'{STATUS[k][0]} {v}' for k, v in counts.items() if v)}), {len(verif)} vérifications, {len(parque)} parqués, {len(journal)} entrées de journal ({len(doc) // 1024} Ko)")
