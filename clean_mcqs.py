import re, sys, pathlib

SRC = pathlib.Path('raw.md')  # change to your input markdown
DST = pathlib.Path('master.md')

text = SRC.read_text(encoding='utf-8')

# 1) strip artifacts
text = re.sub(r'width\s*=\s*"[^"]*"|height\s*=\s*"[^"]*"|\{[^\n}]*\}', ' ', text)
text = re.sub(r'\*{3,}|_{3,}', ' ', text)
text = re.sub(r'\n{3,}', '\n\n', text)

# split into rough items by double newline + digit period pattern as anchor fallback
chunks = re.split(r'\n\s*(?=\d+\.|\*\*\s*\d+)', text)

MODULES = {
    'Psychiatry': r'mania|schizo|histrionic|depress|anxiety|bipolar',
    'Ophthalmology': r'retina|hyphema|uveitis|anisocoria|photophobia|fundus',
    'Obstetrics & Gynecology': r'cervix|labor|ROM|effaced|gravida|obstetric',
    'Pulmonology': r'wheez|asthma|spirom|bronchi',
    'Internal Medicine': r'HTN|hypertension|DM|diabet|microaneurysm|retinopathy',
    'Dermatology': r'squamous|basal|melanoma|ulcer|sun-exposed',
}

compiled = {k: re.compile(v, re.I) for k,v in MODULES.items()}

buckets = {k: [] for k in MODULES}
unknown = []

qid = 1

def classify(s):
    for mod, pat in compiled.items():
        if pat.search(s):
            return mod
    return None

clean_items = []
for raw in chunks:
    s = raw.strip()
    if not s:
        continue
    # create question line
    # Try to extract a question sentence (ends with ? or statement -> make question)
    qline = s.split('\n')[0].strip('* ').strip()
    if not qline.endswith('?'):
        qline = re.sub(r'\s*->\s*', ' leads to ', qline)
        qline = qline.rstrip('.') + '?'  # force question form

    # Collect options from following lines
    opts = []
    for line in s.split('\n')[1:]:
        m = re.match(r'\s*[-*]?\s*([A-Ea-e])[\).]\s*(.+)', line)
        if m:
            opts.append((m.group(1).upper(), m.group(2).strip()))
    # If no options, generate placeholders
    if not opts:
        opts = [('A', 'Option 1 (AI generated)'),
                ('B', 'Option 2 (AI generated)'),
                ('C', 'Option 3 (AI generated)'),
                ('D', 'Option 4 (AI generated)')]

    # Module guess
    mod = classify(s)
    block = f"{qid}. {qline}\n" + '\n'.join([f"- {lab}) {txt}" for lab, txt in opts]) + "\n\n**Answer:** (AI to decide; do not read document answer key)\n**Hint:** (short concept-based clue)\n\n---\n"

    if mod:
        buckets[mod].append(block)
    else:
        unknown.append(block)
    qid += 1

# Write out
out = ['# EMREE MCQ Bank (Clean)\n']
for mod, items in buckets.items():
    if not items: continue
    out.append(f"\n## {mod}\n\n" + ''.join(items))

if unknown:
    out.append("\n## General Medicine\n\n" + ''.join(unknown))

DST.write_text('\n'.join(out), encoding='utf-8')
print('Wrote', DST)
