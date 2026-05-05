"""
refresh_dashboard.py
Queries Google Sheets (6 forms) + Power BI (env only) across 3 time periods,
updates the DATA block in index.html, and pushes to GitHub.

Runs hourly 6 AM–6 PM via Windows Task Scheduler.
"""
import sys, os, re, subprocess, logging, csv, io, urllib.parse
from datetime import date, datetime, timedelta
import pandas as pd
import requests

sys.path.insert(0, r"C:\Users\RSwift\.claude\skills\powerbi-query")
from pbi_helpers import get_delegated_token, execute_dax

# ── Config ─────────────────────────────────────────────────────────────────
REPO_DIR   = r"C:\Users\RSwift\Calude Code Local"
TASKS_XL   = r"C:\Users\RSwift\OneDrive - faenergyus\General\OPERATIONS\Weekly Pumper Meeting\Weekly Pumper Work Items.xlsx"
AVO_XL     = r"C:\Users\RSwift\OneDrive - faenergyus\General\OPERATIONS\Latest Reports\AVO inspection forms.xlsx"
WAHA_LOG   = r"C:\AI\CLAUDE\WAHA\price_alert.log"
TASK_COLS  = ['Gas Well Surveillance', 'Well Test', 'Fluid Level']
INDEX_HTML = os.path.join(REPO_DIR, "index.html")
LOG_FILE   = r"C:\AI\Claude\refresh_dashboard.log"

# AVO name normalization: raw name → dashboard standard name
AVO_NAME_MAP = {
    'henry lozoya': 'Henry',
    'jason martinez': 'Jason',
    'raúl': 'Raul',
    'raul': 'Raul',
    'oswaldo': 'Waldo',
    'armando': 'Armando',
}

# General form name normalization (first/last word matched against this map)
FORM_NAME_MAP = {
    'armando': 'Armando', 'mando': 'Mando', 'hinojosa': 'Armando',
    'henry': 'Henry', 'lozoya': 'Henry',
    'jason': 'Jason', 'martinez': 'Jason',
    'raúl': 'Raul', 'raul': 'Raul',
    'oswaldo': 'Waldo', 'waldo': 'Waldo',
    'eli': 'Eli', 'elias': 'Eli',
    'wynn': 'Wynn', 'jessop': 'Wynn',
    'ryan': 'Ryan', 'swift': 'Ryan',
    'leo': 'Leo', 'aranda': 'Leo',
    'aaron': 'Aaron', 'hernandez': 'Aaron',
    'james': 'James', 'jm9221775': 'James',
    'marisa': 'Marisa',
    'adam': 'Adam', 'holcomb': 'Adam',
    'tyler': 'Tyler',
    'hux': 'Hux',
    'andy': 'Andy',
    'shane': 'Shane',
}

# Google Sheets form definitions:
# (js_key, sheet_id, tab_name, date_col_candidates, person_col_candidates, well_col_candidates)
SHEETS_FORMS = [
    ("gwi",      "1uICvI9zAz9Ai4Snpcee54RoDg0v-rYPoqylsZvs4p60", "Gas Well Inspection",
                 ["Inspection Date", "Date"], ["Inspected By"], ["Well Site"]),
    ("fap",      "146yuHYjs3RF3wtCK3Qj9NXH94DrStwhieTGqPeLQRfA", "Form Responses 1",
                 ["FAP Date", "Timestamp"], ["FAP Shot By", "Shot By"], ["Well Name"]),
    ("pumpup",   "146yuHYjs3RF3wtCK3Qj9NXH94DrStwhieTGqPeLQRfA", "Pump Up Responses",
                 ["Test Date", "Date", "Timestamp"], ["Test Performed By", "Performed By"], ["Well Name"]),
    ("wellsite", "146yuHYjs3RF3wtCK3Qj9NXH94DrStwhieTGqPeLQRfA", "Well Inspection Report",
                 ["Inspection Date", "Date", "Timestamp"], ["Inspected By", "Well Site"], ["Well Site", "Inspection Date"]),
    ("facility", "146yuHYjs3RF3wtCK3Qj9NXH94DrStwhieTGqPeLQRfA", "Facility Inspection Responses",
                 ["Inspection Date", "Date", "Timestamp"], ["Inspected by", "Inspected By"], ["Facility Name", "Facility"]),
    ("whs",      "146yuHYjs3RF3wtCK3Qj9NXH94DrStwhieTGqPeLQRfA", "Grounding",
                 ["Date", "Timestamp"], ["Pumper"], ["Well Name"]),
]

# PBI-only forms (not in Google Sheets)
PBI_FORMS = [
    ("env", "Env Report", "Timestamp", "Submittal By", None),
]


# ── Logging ────────────────────────────────────────────────────────────────
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

# ── Date ranges ────────────────────────────────────────────────────────────
def get_date_range(period: str):
    today = date.today()
    if period == "pastweek":
        return today - timedelta(days=7), today
    elif period == "ytd":
        return date(today.year, 1, 1), today
    elif period == "lastyear":
        return date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)
    raise ValueError(f"Unknown period: {period}")

# ── Google Sheets query ────────────────────────────────────────────────────
def normalize_form_name(raw: str) -> str:
    """Normalize a raw form-submission name to the dashboard standard name."""
    if not raw:
        return raw
    key = raw.strip().lower()
    if key in FORM_NAME_MAP:
        return FORM_NAME_MAP[key]
    parts = key.split()
    if parts and parts[0] in FORM_NAME_MAP:
        return FORM_NAME_MAP[parts[0]]
    if parts and parts[-1] in FORM_NAME_MAP:
        return FORM_NAME_MAP[parts[-1]]
    return raw.strip().title()

def query_form_sheets(key, sheet_id, tab_name, date_cols, person_cols, well_cols, start, end):
    """Read a Google Sheet via gviz CSV. Returns (total, by_pumper, wells_by_pumper)."""
    from collections import defaultdict
    url = (f"https://docs.google.com/spreadsheets/d/{sheet_id}"
           f"/gviz/tq?tqx=out:csv"
           f"&sheet={urllib.parse.quote(tab_name)}"
           f"&headers=1")
    try:
        r = requests.get(url, timeout=30)
        r.raise_for_status()
    except Exception as e:
        log.warning(f"Sheets fetch failed for {key}: {e}")
        return 0, {}, {}

    reader   = csv.reader(io.StringIO(r.text))
    headers  = [h.strip() for h in next(reader)]

    # All date/person/well column indices in priority order
    date_idxs   = [headers.index(c) for c in date_cols   if c in headers]
    person_idxs = [headers.index(c) for c in person_cols if c in headers]
    well_idxs   = [headers.index(c) for c in well_cols   if c in headers] if well_cols else []

    if not date_idxs or not person_idxs:
        log.warning(f"Columns not found for '{key}' in '{tab_name}'. "
                    f"date={date_cols} person={person_cols} available={headers[:10]}")
        return 0, {}, {}

    import re as _re
    _date_pat = _re.compile(r'^\d{1,4}[-/]\d{1,2}[-/]\d{2,4}')

    def _pick_value(row, idxs, reject_dates=False, reject_pumpers=False):
        """Return first non-blank cell value that passes the rejection filters."""
        for i in idxs:
            if i >= len(row):
                continue
            v = row[i].strip()
            if not v:
                continue
            if reject_dates and _date_pat.match(v):
                continue
            if reject_pumpers and v.strip().lower() in FORM_NAME_MAP:
                continue
            return v
        return None

    by_pumper  = defaultdict(int)
    wells_by_p = defaultdict(list)
    for row in reader:
        # Date: try each date column; use first non-blank parseable value
        dv = None
        for di in date_idxs:
            if di < len(row) and row[di].strip():
                try:
                    dv = pd.to_datetime(row[di], errors='coerce')
                    if not pd.isna(dv):
                        break
                except Exception:
                    pass
        if dv is None or pd.isna(dv) or dv.date() < start or dv.date() > end:
            continue
        # Person: skip columns whose value looks like a date (misaligned portal rows)
        raw_person = _pick_value(row, person_idxs, reject_dates=True)
        person = normalize_form_name(raw_person) if raw_person else None
        if not person:
            continue
        by_pumper[person] += 1
        # Well: skip columns whose value looks like a pumper name (misaligned portal rows)
        if well_idxs:
            well = _pick_value(row, well_idxs, reject_pumpers=True, reject_dates=True)
            if well and well not in wells_by_p[person]:
                wells_by_p[person].append(well)

    total = sum(by_pumper.values())
    return total, dict(by_pumper), {k: sorted(v) for k, v in wells_by_p.items()}

# ── PBI query (env only) ───────────────────────────────────────────────────
def query_form_pbi(token, table, date_col, person_col, start, end):
    """Returns {person_name: count} for the given PBI table/period."""
    dax = (
        f"EVALUATE\n"
        f"CALCULATETABLE(\n"
        f"    SUMMARIZE('{table}', '{table}'[{person_col}], \"Count\", COUNTROWS('{table}')),\n"
        f"    '{table}'[{date_col}] >= DATE({start.year},{start.month},{start.day}),\n"
        f"    '{table}'[{date_col}] <= DATE({end.year},{end.month},{end.day})\n"
        f")"
    )
    try:
        rows = execute_dax(token, dax)
        result = {}
        for row in rows:
            vals = list(row.values())
            if len(vals) >= 2 and vals[0] and vals[1]:
                name  = str(vals[0]).strip()
                count = int(vals[1])
                if name and count > 0:
                    result[name] = count
        return result
    except Exception as e:
        log.warning(f"PBI query failed for '{table}': {e}")
        return {}

# ── Build data dict ────────────────────────────────────────────────────────
def build_data():
    avo_data = read_avo_data()
    data     = {}
    for period in ("pastweek", "ytd", "lastyear"):
        start, end = get_date_range(period)
        log.info(f"Period {period}: {start} → {end}")
        data[period] = {}
        # AVO comes first (from Excel)
        data[period]["avo"] = avo_data[period]
        # Google Sheets forms
        for key, sheet_id, tab_name, date_cols, person_cols, well_cols in SHEETS_FORMS:
            total, by_pumper, wells_by_p = query_form_sheets(
                key, sheet_id, tab_name, date_cols, person_cols, well_cols, start, end)
            data[period][key] = {"total": total, "byPumper": by_pumper, "wellsByPumper": wells_by_p}
            log.info(f"  {key:10s} {total}")
        # PBI-only forms (env)
        token = get_delegated_token()
        for key, table, date_col, person_col, well_col in PBI_FORMS:
            by_pumper  = query_form_pbi(token, table, date_col, person_col, start, end)
            total      = sum(by_pumper.values())
            data[period][key] = {"total": total, "byPumper": by_pumper, "wellsByPumper": {}}
            log.info(f"  {key:10s} {total}")
    return data

# ── Price fetchers ─────────────────────────────────────────────────────────
def read_waha_price():
    try:
        with open(WAHA_LOG, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        matches = re.findall(
            r'(\d{4}-\d{2}-\d{2}) \d+:\d+:\d+.*?NG-WAH-WTX-SNL Current Day:\s*([-\d.]+)\s+Prior Day:\s*([-\d.]+)',
            content
        )
        if matches:
            date_str, current, prior = matches[-1]
            price = float(current)
            chg   = round(price - float(prior), 3)
            d = datetime.strptime(date_str, '%Y-%m-%d')
            return {'price': price, 'chg': chg, 'date': d.strftime('%#m/%#d/%Y')}
    except Exception as e:
        log.warning(f"Could not read WAHA price: {e}")
    return None

def fetch_wti_price():
    try:
        url = 'https://query1.finance.yahoo.com/v8/finance/chart/CL=F?interval=1d&range=2d'
        r = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
        meta = r.json()['chart']['result'][0]['meta']
        price = float(meta['regularMarketPrice'])
        prev  = float(meta.get('chartPreviousClose') or meta.get('previousClose') or price)
        chg   = round(price - prev, 2)
        return {'price': price, 'chg': chg, 'date': datetime.now().strftime('%#m/%#d/%Y')}
    except Exception as e:
        log.warning(f"Could not fetch WTI price: {e}")
    return None

def render_prices_js(wti, waha):
    def js_obj(d):
        if not d:
            return 'null'
        return (f'{{price:{d["price"]}, chg:{d["chg"]}, date:"{d["date"]}"}}')
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    return (
        f'// <<PRICES_START>>\n'
        f'const PRICES = {{  // auto-refreshed {ts}\n'
        f'  wti:  {js_obj(wti)},\n'
        f'  waha: {js_obj(waha)}\n'
        f'}};\n'
        f'// <<PRICES_END>>'
    )

# ── Pumper task reader ─────────────────────────────────────────────────────
def read_week(df):
    """Parse one sheet's DataFrame into {date, tasks} dict."""
    if df is None or df.empty:
        return None
    week_val = df['Week'].dropna().iloc[0]
    week_date = week_val.strftime('%#m/%#d/%Y') if hasattr(week_val, 'strftime') else str(week_val)
    tasks = {}
    for _, row in df.iterrows():
        pumper = str(row.get('Pumper', '') or '').strip()
        if not pumper or pumper.lower() == 'nan':
            continue
        entry = {}
        for col in TASK_COLS:
            val = row.get(col, '')
            entry[col] = '' if (val is None or (isinstance(val, float) and pd.isna(val))) else str(val).strip()
        tasks[pumper] = entry
    return {'date': week_date, 'tasks': tasks}

def read_pumper_tasks():
    try:
        import shutil, tempfile
        tmp = tempfile.mktemp(suffix='.xlsx')
        shutil.copy2(TASKS_XL, tmp)          # copy avoids Excel file-lock
        sheets = pd.read_excel(tmp, sheet_name=None)
        try: os.unlink(tmp)
        except Exception: pass
        current = read_week(sheets.get('Current Week'))
        # Last week: most recent row in Historical
        last_week = None
        hist = sheets.get('Historical')
        if hist is not None and not hist.empty:
            try:
                hist['_dt'] = pd.to_datetime(hist['Week'], errors='coerce')
                max_dt = hist['_dt'].max()
                most_recent = hist[hist['_dt'] == max_dt].drop(columns=['_dt'])
                last_week = read_week(most_recent)
            except Exception:
                pass
        log.info(f"Pumper tasks: current={current['date'] if current else None}, last={last_week['date'] if last_week else None}")
        return current, last_week
    except Exception as e:
        log.warning(f"Could not read pumper tasks: {e}")
        return None, None

def normalize_avo_name(raw: str) -> str:
    """Normalize AVO pumper names to dashboard standard names."""
    if not raw:
        return raw
    s = raw.strip()
    key = s.lower().rstrip()
    # Try exact match first
    if key in AVO_NAME_MAP:
        return AVO_NAME_MAP[key]
    # Try prefix match (e.g. "Henry Lozoya" → check "henry")
    first_word = key.split()[0] if key.split() else key
    if first_word in AVO_NAME_MAP:
        return AVO_NAME_MAP[first_word]
    # Return title-cased original if no match
    return s.title()

def read_avo_data():
    """
    Read AVO inspection Excel, return {period: {total, byPumper, wellsByPumper}}.
    Periods: pastweek, ytd, lastyear.
    """
    import shutil, tempfile
    from collections import defaultdict
    try:
        tmp = tempfile.mktemp(suffix='.xlsx')
        shutil.copy2(AVO_XL, tmp)
        try:
            xl = pd.ExcelFile(tmp)
            sheet_name = xl.sheet_names[0]   # whatever the (single) tab is named
            log.info(f"  AVO sheet: {sheet_name}")
            df = pd.read_excel(tmp, sheet_name=sheet_name, header=2)
        finally:
            try: os.unlink(tmp)
            except Exception: pass

        df.columns = [str(c).strip() for c in df.columns]
        df = df[['Inspected By', 'Date', 'Item']].copy()
        df = df.dropna(subset=['Inspected By', 'Date'])
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])
        df['_name'] = df['Inspected By'].apply(lambda x: normalize_avo_name(str(x)))
        df['_item'] = df['Item'].apply(lambda x: str(x).strip() if pd.notna(x) else '')

        today = date.today()
        periods = {
            "pastweek": (today - timedelta(days=7), today),
            "ytd":      (date(today.year, 1, 1), today),
            "lastyear": (date(today.year - 1, 1, 1), date(today.year - 1, 12, 31)),
        }

        result = {}
        for period, (start, end) in periods.items():
            mask = (df['Date'].dt.date >= start) & (df['Date'].dt.date <= end)
            sub  = df[mask]
            by_pumper  = sub.groupby('_name').size().to_dict()
            wells_dict = defaultdict(list)
            for _, row in sub.iterrows():
                p = row['_name']
                w = row['_item']
                if w and w not in wells_dict[p]:
                    wells_dict[p].append(w)
            wells_by_p = {k: sorted(v) for k, v in wells_dict.items()}
            total = sum(by_pumper.values())
            result[period] = {"total": total, "byPumper": by_pumper, "wellsByPumper": wells_by_p}
            log.info(f"  AVO {period:10s} {total}")
        return result
    except Exception as e:
        log.warning(f"Could not read AVO data: {e}")
        return {p: {"total": 0, "byPumper": {}, "wellsByPumper": {}} for p in ("pastweek", "ytd", "lastyear")}

def render_tasks_js(current, last_week):
    def week_js(w):
        if not w:
            return 'null'
        lines = ['{']
        lines.append(f'    date: "{w["date"]}",')
        lines.append('    tasks: {')
        for pumper, cols in w['tasks'].items():
            p = pumper.replace('\\', '\\\\').replace('"', '\\"')
            lines.append(f'      "{p}": {{')
            for col in TASK_COLS:
                val = cols.get(col, '').replace('\\', '\\\\').replace('"', '\\"').replace('\r\n', '\\n').replace('\r', '\\n').replace('\n', '\\n')
                lines.append(f'        "{col}": "{val}",')
            lines.append('      },')
        lines.append('    }')
        lines.append('  }')
        return '\n'.join(lines)
    ts = datetime.now().strftime('%Y-%m-%d %H:%M')
    return (
        f'// <<PUMPER_TASKS_START>>\n'
        f'const PUMPER_TASKS = {{  // auto-refreshed {ts}\n'
        f'  currentWeek: {week_js(current)},\n'
        f'  lastWeek: {week_js(last_week)}\n'
        f'}};\n'
        f'// <<PUMPER_TASKS_END>>'
    )

# ── Render JS block ────────────────────────────────────────────────────────
def render_js(data):
    import json as _json
    ts    = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [f"const DATA = {{  // auto-refreshed {ts}"]
    # All keys in display order: avo first, then sheets forms, then pbi forms
    all_keys = ["avo"] + [key for key, *_ in SHEETS_FORMS] + [key for key, *_ in PBI_FORMS]
    for period in ("pastweek", "ytd", "lastyear"):
        lines.append(f"  {period}: {{")
        for key in all_keys:
            fd            = data[period][key]
            total         = fd["total"]
            by_pumper     = fd["byPumper"]
            wells_by_p    = fd.get("wellsByPumper", {})
            if total == 0:
                lines.append(f"    {key:<9}: ZERO(),")
            else:
                bp_inner  = ", ".join(f"'{p}': {c}" for p, c in by_pumper.items())
                wbp_inner = ", ".join(
                    f"'{p}': {_json.dumps(ws)}" for p, ws in wells_by_p.items()
                )
                lines.append(
                    f"    {key:<9}: {{ total: {total}, byPumper: {{ {bp_inner} }}, "
                    f"wellsByPumper: {{ {wbp_inner} }} }},"
                )
        lines.append("  },")
    lines.append("};")
    return "\n".join(lines)

# ── Patch index.html ───────────────────────────────────────────────────────
def update_html(new_data_js, new_tasks_js, new_prices_js, ts):
    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    # Replace const DATA block (lambda avoids re.sub escape processing)
    pattern = r"const DATA = \{.*?\n\};"
    new_html = re.sub(pattern, lambda m: new_data_js, html, flags=re.DOTALL, count=1)
    if new_html == html:
        log.error("DATA block pattern not matched — HTML not updated")
        return False

    # Replace PRICES block
    prices_pattern = r"// <<PRICES_START>>\n.*?\n// <<PRICES_END>>"
    new_html = re.sub(prices_pattern, new_prices_js, new_html, flags=re.DOTALL, count=1)

    # Replace PUMPER_TASKS block
    tasks_pattern = r"// <<PUMPER_TASKS_START>>\n.*?\n// <<PUMPER_TASKS_END>>"
    new_html = re.sub(tasks_pattern, lambda m: new_tasks_js, new_html, flags=re.DOTALL, count=1)

    # Update footer timestamp
    note_pattern = r'(<div class="data-note">).*?(</div>)'
    note_new = rf'\1Dashboard data from Google Sheets · Updated {ts}\2'
    new_html = re.sub(note_pattern, note_new, new_html, count=1)

    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.write(new_html)
    log.info("index.html updated")
    return True

# ── Git push ───────────────────────────────────────────────────────────────
_NO_WIN = {"capture_output": True, "creationflags": subprocess.CREATE_NO_WINDOW}

def git_push(ts):
    subprocess.run(["git", "-C", REPO_DIR, "add", "index.html"],   check=True, **_NO_WIN)
    subprocess.run(["git", "-C", REPO_DIR, "commit", "-m",
                    f"Auto-refresh dashboard data {ts}"],           check=True, **_NO_WIN)
    # Pull remote changes with rebase before pushing to avoid non-fast-forward rejections.
    # If rebase conflicts on index.html (the only file we modify), resolve by taking our version.
    pull = subprocess.run(["git", "-C", REPO_DIR, "pull", "--rebase", "--autostash"],
                          capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    if pull.returncode != 0:
        log.warning(f"git pull --rebase failed: {pull.stderr.strip()[:300]}")
        # Abort rebase if in progress, then force-resolve with ours-strategy merge
        subprocess.run(["git", "-C", REPO_DIR, "rebase", "--abort"],
                       capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        # Fetch + merge with ours strategy for index.html conflicts
        subprocess.run(["git", "-C", REPO_DIR, "fetch", "origin"],
                       capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
        merge = subprocess.run(["git", "-C", REPO_DIR, "merge", "-X", "ours", "origin/main", "-m",
                                f"Auto-merge remote during refresh {ts}"],
                               capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if merge.returncode != 0:
            log.error(f"git merge failed: {merge.stderr.strip()[:300]}")
    # Retry push up to 3 times in case of transient network issues
    for attempt in range(3):
        push = subprocess.run(["git", "-C", REPO_DIR, "push"],
                              capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
        if push.returncode == 0:
            log.info("Pushed to GitHub")
            return
        log.warning(f"git push attempt {attempt+1} failed: {push.stderr.strip()[:300]}")
        if attempt < 2:
            # Pull again in case remote advanced between our pull and push
            subprocess.run(["git", "-C", REPO_DIR, "pull", "--rebase", "--autostash"],
                           capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
    raise RuntimeError("git push failed after 3 attempts")

# ── Main ───────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
    log.info(f"=== Refresh start {ts} ===")
    try:
        data        = build_data()
        new_data_js = render_js(data)
        current_tasks, last_tasks = read_pumper_tasks()
        new_tasks_js  = render_tasks_js(current_tasks, last_tasks)
        wti           = fetch_wti_price()
        waha          = read_waha_price()
        new_prices_js = render_prices_js(wti, waha)
        log.info(f"Prices — WTI: {wti}, WAHA: {waha}")
        ok            = update_html(new_data_js, new_tasks_js, new_prices_js, ts)
        if ok:
            git_push(ts)
        log.info("=== Refresh complete ===")
    except Exception as e:
        log.exception(f"Refresh failed: {e}")
        sys.exit(1)
