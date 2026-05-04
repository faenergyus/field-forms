"""Build WELL_DATA JSON for wellinfo.html.

Master well list: SQL Server sf\\sqldev Ops_Reporting dbo.Pumper_Data_Calcs (959 wells).
WBD source: dbo.wbd_* tables (migrated from well_file_summary.xlsx).
Matching: name-first (with normalization), API fallback.
"""
import json
import re
import pyodbc

HTML = r"C:\Users\RSwift\Calude Code Local\wellinfo.html"
CONN_STR = r"DRIVER={ODBC Driver 17 for SQL Server};SERVER=sf\sqldev;DATABASE=Ops_Reporting;Trusted_Connection=yes;TrustServerCertificate=yes;"

# ----- 1. Load SQL master -----
print("Loading SQL master (Pumper_Data_Calcs)...")
conn = pyodbc.connect(CONN_STR)
cur = conn.cursor()
cur.execute("""
    SELECT [Short Name], [Well Name], [API10 (String)], Company, Status, Type, [Pumper Name], Engineer, Stop, Unit, _LeaseType,
           [WBD Link], WBD_PDFLINK, WellFileLink, Location
    FROM dbo.Pumper_Data_Calcs
    WHERE [Short Name] IS NOT NULL AND LTRIM(RTRIM([Short Name])) <> ''
""")
sql_cols = [d[0] for d in cur.description]
sql_rows = cur.fetchall()
print(f"  {len(sql_rows)} wells")

ABBREV = {
    'WEST EUMONT UNIT': 'WEU', 'WEST EUMONT': 'WEU',
    'EAST EUMONT UNIT': 'EEU', 'EAST EUMONT': 'EEU',
    'NORTH EUMONT UNIT': 'NEU',
    'SOUTH EUMONT UNIT': 'SEU',
    'SOUTH JAL UNIT': 'SJU',
    'NORTH JAL UNIT': 'NJU',
    'WHITE CITY UNIT': 'WCU',
}
def norm(s):
    if not s: return ''
    s = str(s).upper().strip()
    for full, short in ABBREV.items():
        s = s.replace(full, short)
    s = s.replace('#', ' ')
    s = re.sub(r'\b0+(\d)', r'\1', s)
    s = re.sub(r'\s+', ' ', s)
    s = re.sub(r'[^A-Z0-9 ]', '', s)
    return s.strip()

short_by_norm = {}
short_by_api = {}
sql_master = {}
for r in sql_rows:
    rec = dict(zip(sql_cols, r))
    short = (rec['Short Name'] or '').strip()
    if not short: continue
    sql_master[short] = rec
    n = norm(rec['Well Name'])
    if n: short_by_norm[n] = short
    api = str(rec['API10 (String)'] or '').strip()
    if len(api) == 10: short_by_api[api] = short

print(f"  norm-keyed: {len(short_by_norm)}, api-keyed: {len(short_by_api)}")

# ----- 2. Load WBD tables from SQL -----
print("Loading WBD tables from SQL...")
def load_table(sql):
    cur.execute(sql)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]

wells = load_table("SELECT * FROM dbo.wbd_wells")
versions = load_table("SELECT * FROM dbo.wbd_versions WHERE data_extracted = 1")
casing = load_table("SELECT * FROM dbo.wbd_casing")
perfs = load_table("SELECT * FROM dbo.wbd_perforations")
plugs = load_table("SELECT * FROM dbo.wbd_plugs")
ftops = load_table("SELECT * FROM dbo.wbd_formation_tops")
tubing = load_table("SELECT * FROM dbo.wbd_tubing")
rods = load_table("SELECT * FROM dbo.wbd_rods")

print(f"  wells={len(wells)}, versions={len(versions)} (extracted), casing={len(casing)}, perfs={len(perfs)}, plugs={len(plugs)}, ftops={len(ftops)}, tubing={len(tubing)}, rods={len(rods)}")

def by_wbd(rows):
    out = {}
    for r in rows:
        wid = r.get('wbd_id')
        if wid is None: continue
        out.setdefault(wid, []).append(r)
    return out

csg_by_wbd = by_wbd(casing)
pf_by_wbd = by_wbd(perfs)
pl_by_wbd = by_wbd(plugs)
ft_by_wbd = by_wbd(ftops)
tb_by_wbd = by_wbd(tubing)
rd_by_wbd = by_wbd(rods)
versions_by_well = {}
for v in versions:
    versions_by_well.setdefault(v['well_id'], []).append(v)

# ----- 3. Match xlsx wells -> short names (name-first, api fallback) -----
print("Matching wells...")
matched_name = matched_api = unmatched = 0
conflicts = []
well_to_short = {}

for w in wells:
    xname = w.get('well_name') or ''
    api = str(w.get('api') or '').strip()
    api10 = api.replace('-', '')[:10]
    n = norm(xname)
    short_by_n = short_by_norm.get(n)
    short_by_a = short_by_api.get(api10) if len(api10) == 10 else None

    if short_by_n:
        short = short_by_n
        matched_name += 1
        if short_by_a and short_by_a != short_by_n:
            conflicts.append((xname, api, short_by_n, short_by_a))
    elif short_by_a:
        short = short_by_a
        matched_api += 1
    else:
        unmatched += 1
        continue
    well_to_short[w['well_id']] = short

print(f"  Matched name-first: {matched_name}, api-fallback: {matched_api}, total: {matched_name+matched_api}/{len(wells)}")

# ----- 4. Build WELL_DATA JSON -----
def fmt_csg(r):
    return {'ty': r.get('casing_type'), 'sz': r.get('size'), 'wt': r.get('weight'),
            'gr': r.get('grade'),
            'dp': str(r['set_depth']) if r.get('set_depth') is not None else None,
            'hs': r.get('hole_size'),
            'cs': str(r['cement_sacks']) if r.get('cement_sacks') is not None else None,
            'tc': r.get('toc')}
def fmt_pf(r):
    return {'td': r.get('top_depth'), 'bd': r.get('bottom_depth'),
            'spf': r.get('spf'), 'zn': r.get('zone'),
            'dt': str(r['perf_date'])[:10] if r.get('perf_date') else None,
            'sq': bool(r['is_squeezed']) if r.get('is_squeezed') is not None else None}
def fmt_pl(r):
    return {'ty': r.get('plug_type'), 'dp': r.get('depth'), 'tc': r.get('toc'), 'cs': r.get('cement_sacks')}
def fmt_ft(r):
    return {'fm': r.get('formation_name'), 'dp': r.get('depth')}
def fmt_tb(r):
    return {'desc': r.get('description'), 'dp': r.get('depth'), 'jts': r.get('joints')}
def fmt_rd(r):
    return {'desc': r.get('description'), 'cnt': r.get('count'), 'len': r.get('length'), 'dp': r.get('depth')}

WELL_DATA = {}
for short, rec in sql_master.items():
    api = str(rec['API10 (String)'] or '').strip()
    WELL_DATA[short] = {
        'fn': rec['Well Name'], 'sn': short, 'api': api,
        'loc': rec['Location'] or '', 'co': rec['Company'] or '',
        'stat': rec['Status'] or '', 'ty': rec['Type'] or '',
        'pmpr': rec['Pumper Name'] or '', 'engr': rec['Engineer'] or '',
        'stop': rec['Stop'] or '', 'unit': rec['Unit'] or '',
        'lt': rec['_LeaseType'] or '',
        'wbd_link': rec['WBD Link'] or '', 'wbd_pdf': rec['WBD_PDFLINK'] or '',
        'well_link': rec['WellFileLink'] or '',
        'v': [],
    }

for well_id, short in well_to_short.items():
    if short not in WELL_DATA: continue
    out = []
    for v in versions_by_well.get(well_id, []):
        wid = v['wbd_id']
        out.append({
            'id': wid,
            'dt': str(v['wbd_date'])[:10] if v.get('wbd_date') else None,
            'st': v.get('status') or '',
            'td': str(v['td']) if v.get('td') is not None else None,
            'pb': str(v['pbtd']) if v.get('pbtd') is not None else None,
            'csg': [fmt_csg(c) for c in csg_by_wbd.get(wid, [])],
            'pf':  [fmt_pf(p) for p in pf_by_wbd.get(wid, [])],
            'pl':  [fmt_pl(p) for p in pl_by_wbd.get(wid, [])],
            'ft':  [fmt_ft(f) for f in ft_by_wbd.get(wid, [])],
            'tb':  [fmt_tb(t) for t in tb_by_wbd.get(wid, [])],
            'rd':  [fmt_rd(r) for r in rd_by_wbd.get(wid, [])],
        })
    def sortkey(x):
        return (0 if x['st']=='CURRENT' else 1, -(int((x['dt'] or '0000-00-00')[:4]) if x['dt'] else 0))
    out.sort(key=sortkey)
    WELL_DATA[short]['v'] = out

with_data = sum(1 for v in WELL_DATA.values() if v['v'])
print(f"  Wells with WBD data: {with_data}/{len(WELL_DATA)}")

# ----- 5. Inject into HTML -----
print("Injecting into wellinfo.html...")
with open(HTML, 'r', encoding='utf-8') as f:
    html = f.read()
start = html.find('var WELL_DATA = ')
i = html.find('{', start); depth = 0
while i < len(html):
    c = html[i]
    if c == '{': depth += 1
    elif c == '}':
        depth -= 1
        if depth == 0: break
    i += 1
end_brace = i
assert html[end_brace:end_brace+2] == '};'
new_json = json.dumps(WELL_DATA, separators=(',', ':'), ensure_ascii=False)
new_html = html[:start] + 'var WELL_DATA = ' + new_json + html[end_brace+1:]
with open(HTML, 'w', encoding='utf-8') as f:
    f.write(new_html)

print(f"  HTML written: {len(new_html):,} bytes")
conn.close()
print("Done.")
