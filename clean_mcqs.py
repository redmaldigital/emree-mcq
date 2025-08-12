import re, pathlib

SRC = pathlib.Path("raw.md")     # input
DST = pathlib.Path("master.md")  # output

text = SRC.read_text(encoding="utf-8")

# --- Normalize Word/HTML artifacts ---
text = re.sub(r'width\s*=\s*"[^"]*"|height\s*=\s*"[^"]*"|\{[^\n}]*\}', " ", text)
text = re.sub(r"\*{3,}|_{3,}", " ", text)   # collapse *** ___
text = re.sub(r"\r", "", text)              # CRLF -> LF
text = re.sub(r"\t", " ", text)
text = re.sub(r"\n{3,}", "\n\n", text)      # squeeze blank lines

lines = text.split("\n")

# --- Patterns ---
opt_pat = re.compile(r'^\s*[-*]?\s*([A-Ea-e])[\).]\s*(.+)')            # A) text
q_num_pat = re.compile(r'^\s*(?:\d+|[ivxlcdmIVXLCDM]+)[\).]?\s*(.*)')   # 12. text  or  xii) text
q_line_pat = re.compile(r'.+\?\s*$')                                    # ends with ?

MODULES = {
    "Psychiatry": r"mania|schizo|histrionic|depress|anxiety|bipolar|psych|SSRI|panic",
    "Ophthalmology": r"retina|hyphema|uveitis|anisocoria|photophobia|fundus|vision|optic",
    "Obstetrics & Gynecology": r"cervix|labor|ROM|effaced|gravida|pregnan|obstetric|amenorrhea",
    "Pulmonology": r"wheez|asthma|spirom|bronchi|COPD|respiratory",
    "Internal Medicine": r"HTN|hypertension|DM|diabet|microaneurysm|retinopathy|thyroid|pancreatitis",
    "Dermatology": r"squamous|basal|melanoma|ulcer|sun-exposed|dermat",
}
compiled = {k: re.compile(v, re.I) for k, v in MODULES.items()}

# --- Find anchors: any line ending with ? OR a numbered start that looks like a question ---
anchors = [i for i, ln in enumerate(lines) if q_line_pat.match(ln.strip())]
for i, ln in enumerate(lines):
    m = q_num_pat.match(ln.strip())
    if m and ("?" in m.group(1)) and i not in anchors:
        anchors.append(i)
anchors = sorted(set(anchors)) or [i for i, ln in enumerate(lines) if opt_pat.match(ln)]  # fallback

# --- Build tentative blocks between anchors; split further if multiple ? in a block ---
blocks = []
for idx, start in enumerate(anchors):
    end = anchors[idx + 1] if idx + 1 < len(anchors) else len(lines)
    seg = lines[start:end]

    # If multiple question marks inside, split into sub‑blocks at each '?'
    q_idxs = [i for i, ln in enumerate(seg) if q_line_pat.match(ln.strip())]
    if len(q_idxs) > 1:
        for j, si in enumerate(q_idxs):
            sj = q_idxs[j + 1] if j + 1 < len(q_idxs) else len(seg)
            blocks.append(seg[si:sj])
    else:
        blocks.append(seg)

def guess_module(text_block: str) -> str:
    for name, pat in compiled.items():
        if pat.search(text_block):
            return name
    return "General Medicine"

items = []
for seg in blocks:
    seg = [s for s in seg if s.strip() != ""]
    if not seg: 
        continue

    # 1) Question line
    qline = None
    for ln in seg:
        if q_line_pat.match(ln.strip()):
            qline = ln.strip()
            break
    if not qline:
        m = q_num_pat.match(seg[0].strip())
        base = (m.group(1).strip() if m else seg[0].strip())
        if not base:
            base = "Select the most appropriate option"
        if not base.endswith("?"):
            base += "?"
        qline = base

    # 2) Options
    opts = []
    start_collect = False
    for ln in seg:
        if ln.strip() == qline:
            start_collect = True
            continue
        if start_collect:
            m = opt_pat.match(ln)
            if m:
                opts.append((m.group(1).upper(), m.group(2).strip()))
            # stop if we hit a new question inside the same block
            if q_line_pat.match(ln.strip()):
                break

    # If none gathered after qline, harvest any options anywhere in seg
    if not opts:
        for ln in seg:
            m = opt_pat.match(ln)
            if m:
                opts.append((m.group(1).upper(), m.group(2).strip()))

    # If still none, fabricate placeholders
    if not opts:
        opts = [
            ("A", "Option 1 (AI generated)"),
            ("B", "Option 2 (AI generated)"),
            ("C", "Option 3 (AI generated)"),
            ("D", "Option 4 (AI generated)"),
        ]

    # Deduplicate A–E, keep first occurrence
    seen, dedup = set(), []
    for lab, txt in opts:
        if lab not in seen:
            seen.add(lab)
            dedup.append((lab, txt))
    opts = dedup[:5]

    # 3) Module
    mod = guess_module(" ".join(seg))

    items.append((mod, qline, opts))

# --- Write out ---
qid = 1
out = ["# EMREE MCQ Bank (Clean)\n"]
current_mod = None

for mod, qline, opts in items:
    if mod != current_mod:
        out.append(f"\n## {mod}\n")
        current_mod = mod
    block = [f"\n{qid}. {qline}"]
    for lab, txt in opts:
        block.append(f"- {lab}) {txt}")
    block.append("\n**Answer:** (AI to decide; do not read document answer key)")
    block.append("**Hint:** (short concept-based clue)\n\n---")
    out.append("\n".join(block))
    qid += 1

DST.write_text("\n".join(out) + "\n", encoding="utf-8")
print("Wrote", DST)
