"""Generate pumpup.html — Pump Up Entry form with photo upload."""
import json, sys

sys.path.insert(0, r"C:\Users\RSwift\.claude\skills\powerbi-query")
from pbi_helpers import get_delegated_token, execute_dax

print("Querying Operations for oil wells...")
token = get_delegated_token()
rows = execute_dax(token, """
EVALUATE
CALCULATETABLE(
    VALUES('Pumper Data'[Well Name]),
    'Pumper Data'[TypeX] = "Oil"
)
ORDER BY 'Pumper Data'[Well Name]
""")
wells = sorted(set(r['Well Name'] for r in rows if r.get('Well Name')))
print(f"  {len(wells)} oil wells loaded from Operations")

wells_js = json.dumps(wells)

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <title>Pump Up Entry</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f4f0; color: #1a1a1a; min-height: 100vh; }}
    .header {{ background: #1c4a1c; padding: 12px 16px; display: flex; align-items: center; gap: 12px; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 10px rgba(0,0,0,0.25); }}
    .header h1 {{ font-size: 1.1rem; color: #5dc85d; font-weight: 700; flex: 1; }}
    .header a {{ color: #90bc90; text-decoration: none; font-size: 0.8rem; }}
    .container {{ max-width: 600px; margin: 0 auto; padding: 16px; }}
    .section {{ background: #fff; border-radius: 9px; padding: 16px; margin-bottom: 12px; border-left: 4px solid #3a8a3a; box-shadow: 0 1px 4px rgba(0,0,0,0.07); }}
    .section-title {{ color: #4a724a; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 12px; }}
    label {{ display: block; color: #3a5a3a; font-size: 0.85rem; margin-bottom: 4px; font-weight: 500; }}
    .required::after {{ content: " *"; color: #c0392b; }}
    input[type="text"], input[type="date"], input[type="number"], select, textarea {{
      width: 100%; padding: 9px 12px; background: #fff; border: 1.5px solid #c8ddc8;
      border-radius: 6px; color: #1a1a1a; font-size: 16px; margin-bottom: 12px;
      -webkit-appearance: none;
    }}
    input:focus, select:focus, textarea:focus {{ outline: none; border-color: #3a8a3a; box-shadow: 0 0 0 2px rgba(58,138,58,0.15); }}
    input.input-error {{ border-color: #c0392b !important; background: #fff5f5; }}
    .field-error {{ color: #c0392b; font-size: 0.75rem; margin-top: -8px; margin-bottom: 8px; display: none; }}
    .field-error.show {{ display: block; }}
    textarea {{ min-height: 60px; resize: vertical; }}
    .radio-group {{ display: flex; gap: 8px; margin-bottom: 12px; }}
    .radio-btn {{ flex: 1; }}
    .radio-btn input {{ display: none; }}
    .radio-btn label {{ display: block; text-align: center; padding: 8px; background: #f5faf5; border: 1.5px solid #c8ddc8; border-radius: 6px; cursor: pointer; color: #3a5a3a; font-size: 0.9rem; }}
    .radio-btn input:checked + label {{ background: #eaf5ea; border-color: #3a8a3a; color: #1c4a1c; font-weight: 600; }}

    /* Autocomplete */
    .autocomplete-wrap {{ position: relative; }}
    .autocomplete-wrap input {{ margin-bottom: 0; }}
    .autocomplete-list {{ position: absolute; top: 100%; left: 0; right: 0; background: #fff; border: 1.5px solid #3a8a3a; border-top: none; border-radius: 0 0 6px 6px; max-height: 200px; overflow-y: auto; z-index: 50; display: none; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
    .autocomplete-list div {{ padding: 10px 12px; cursor: pointer; font-size: 0.9rem; border-bottom: 1px solid #eaf5ea; color: #1a1a1a; }}
    .autocomplete-list div:hover, .autocomplete-list div.active {{ background: #eaf5ea; color: #1c4a1c; }}
    .autocomplete-list div mark {{ background: none; color: #2d7a2d; font-weight: 700; }}
    .well-count {{ font-size: 0.7rem; color: #6a8a6a; margin-top: 4px; margin-bottom: 12px; }}

    /* Photo grid */
    .photo-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin-bottom: 12px; }}
    .photo-thumb {{ position: relative; aspect-ratio: 1; background: #f5faf5; border-radius: 6px; overflow: hidden; border: 1.5px solid #c8ddc8; }}
    .photo-thumb img {{ width: 100%; height: 100%; object-fit: cover; }}
    .photo-thumb .remove {{ position: absolute; top: 4px; right: 4px; background: rgba(0,0,0,0.6); color: #fff; border: none; border-radius: 50%; width: 22px; height: 22px; font-size: 0.8rem; cursor: pointer; display: flex; align-items: center; justify-content: center; }}
    .photo-add {{ aspect-ratio: 1; background: #f5faf5; border: 2px dashed #c8ddc8; border-radius: 6px; display: flex; align-items: center; justify-content: center; font-size: 2rem; color: #8aaa8a; cursor: pointer; }}
    .photo-add:hover {{ background: #eaf5ea; border-color: #3a8a3a; color: #3a8a3a; }}
    .upload-progress {{ font-size: 0.85rem; color: #3a5a3a; margin-top: 8px; display: none; }}

    .submit-btn {{ width: 100%; padding: 14px; background: #2d7a2d; color: #fff; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; margin-top: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.15); }}
    .submit-btn:active {{ background: #1c5a1c; }}
    .submit-btn:disabled {{ background: #8aaa8a; cursor: not-allowed; }}

    /* Success overlay */
    .overlay {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 200; align-items: center; justify-content: center; flex-direction: column; gap: 16px; }}
    .overlay.show {{ display: flex; }}
    .overlay-card {{ background: #fff; border: 2px solid #3a8a3a; border-radius: 12px; padding: 32px; text-align: center; max-width: 340px; width: 90%; box-shadow: 0 8px 32px rgba(0,0,0,0.2); }}
    .overlay-card .checkmark {{ font-size: 3rem; margin-bottom: 8px; color: #2d7a2d; }}
    .overlay-card h2 {{ color: #1c4a1c; font-size: 1.2rem; margin-bottom: 4px; }}
    .overlay-card p {{ color: #4a724a; font-size: 0.9rem; margin-bottom: 16px; }}
    .overlay-btn {{ padding: 10px 24px; border: none; border-radius: 8px; font-size: 0.95rem; font-weight: 600; cursor: pointer; }}
    .btn-new {{ background: #2d7a2d; color: #fff; }}
  </style>
</head>
<body>

<div class="header">
  <h1>⛽ Pump Up Entry</h1>
  <a href="index.html">← Portal</a>
</div>

<div class="container">
  <form id="pumpup-form">

    <!-- Inspector Info -->
    <div class="section">
      <div class="section-title">Test Info</div>

      <label class="required" for="testPerformedBy">Test Performed By</label>
      <select id="testPerformedBy" required>
        <option value="">Select inspector...</option>
        <option>Andy</option>
        <option>Armando</option>
        <option>Henry</option>
        <option>Jason</option>
        <option>Joe</option>
        <option>Larry</option>
        <option>Raul</option>
        <option>Waldo</option>
        <option>Wynn</option>
      </select>

      <label class="required" for="testDate">Test Date</label>
      <input type="date" id="testDate" required>

      <label class="required" for="wellName">Well Name</label>
      <div class="autocomplete-wrap">
        <input type="text" id="wellName" placeholder="Type to search oil wells..." autocomplete="off" required>
        <div class="autocomplete-list" id="wellList"></div>
      </div>
      <div class="well-count" id="wellCount"></div>
    </div>

    <!-- Test Results -->
    <div class="section">
      <div class="section-title">Test Results</div>

      <label for="runTimePct">Run Time %</label>
      <input type="text" id="runTimePct" class="num-field" inputmode="decimal" placeholder="0–100">
      <div class="field-error" id="err-runTimePct">Enter a number (e.g. 85)</div>

      <label for="strokesTo500"># of Strokes to 500 psi</label>
      <input type="text" id="strokesTo500" class="num-field" inputmode="numeric" placeholder="e.g. 12">
      <div class="field-error" id="err-strokesTo500">Enter a whole number</div>

      <label>Does it hold 500 psi for 2 minutes?</label>
      <div class="radio-group">
        <div class="radio-btn"><input type="radio" name="holds500" id="holds500-yes" value="Yes"><label for="holds500-yes">Yes</label></div>
        <div class="radio-btn"><input type="radio" name="holds500" id="holds500-no" value="No"><label for="holds500-no">No</label></div>
        <div class="radio-btn"><input type="radio" name="holds500" id="holds500-na" value="N/A"><label for="holds500-na">N/A</label></div>
      </div>
    </div>

    <!-- Pressure -->
    <div class="section">
      <div class="section-title">Pressure Check</div>

      <label for="pumpingPressure">Pumping Pressure Range, psi</label>
      <input type="text" id="pumpingPressure" class="range-field" inputmode="decimal" placeholder="e.g. 50-150">
      <div class="field-error" id="err-pumpingPressure">Enter a range (e.g. 50-150) or single number</div>

      <label>Tagging?</label>
      <div class="radio-group">
        <div class="radio-btn"><input type="radio" name="tagging" id="tagging-yes" value="Yes"><label for="tagging-yes">Yes</label></div>
        <div class="radio-btn"><input type="radio" name="tagging" id="tagging-no" value="No"><label for="tagging-no">No</label></div>
        <div class="radio-btn"><input type="radio" name="tagging" id="tagging-na" value="N/A"><label for="tagging-na">N/A</label></div>
      </div>

      <label for="casingPressure">Casing Pressure, psi</label>
      <input type="text" id="casingPressure" class="num-field" inputmode="decimal" placeholder="e.g. 120">
      <div class="field-error" id="err-casingPressure">Enter a number</div>

      <label>Check Valve Holding?</label>
      <div class="radio-group">
        <div class="radio-btn"><input type="radio" name="checkValve" id="cv-yes" value="Yes"><label for="cv-yes">Yes</label></div>
        <div class="radio-btn"><input type="radio" name="checkValve" id="cv-no" value="No"><label for="cv-no">No</label></div>
        <div class="radio-btn"><input type="radio" name="checkValve" id="cv-na" value="N/A"><label for="cv-na">N/A</label></div>
      </div>
    </div>

    <!-- Production -->
    <div class="section">
      <div class="section-title">Production</div>

      <label for="oilCut">Oil Cut, %</label>
      <input type="text" id="oilCut" class="num-field" inputmode="decimal" placeholder="0–100">
      <div class="field-error" id="err-oilCut">Enter a number (e.g. 65)</div>

      <label for="spm">SPM</label>
      <input type="text" id="spm" class="num-field" inputmode="decimal" placeholder="e.g. 4.5">
      <div class="field-error" id="err-spm">Enter a number</div>
    </div>

    <!-- Notes -->
    <div class="section">
      <div class="section-title">Notes</div>
      <label for="notes">Notes</label>
      <textarea id="notes" placeholder="Any additional observations..."></textarea>
    </div>

    <!-- Photos -->
    <div class="section">
      <div class="section-title">Photos</div>
      <input type="file" id="photoInput" accept="image/*" multiple style="display:none">
      <div class="photo-grid" id="photoGrid">
        <div class="photo-add" id="addPhotoBtn">+</div>
      </div>
      <div class="upload-progress" id="uploadProgress"></div>
    </div>

    <button type="submit" class="submit-btn" id="submitBtn">Submit</button>
  </form>
</div>

<!-- Success overlay -->
<div class="overlay" id="successOverlay">
  <div class="overlay-card">
    <div class="checkmark">✓</div>
    <h2>Submitted!</h2>
    <p id="successMsg"></p>
    <div id="uploadProgress2" style="font-size:0.85rem;color:#3a5a3a;margin-bottom:12px;display:none;"></div>
    <button class="overlay-btn btn-new" id="newEntryBtn" style="display:none;">New Entry</button>
  </div>
</div>

<script>
const FORM_ACTION = 'https://docs.google.com/forms/d/e/1FAIpQLSc366DrGF712zDwzZBy6chnZjqE-d-5XTNUEWcR6pzbEZ3_Nw/formResponse';
const PHOTO_ENDPOINT = 'https://script.google.com/macros/s/AKfycbwOXsEqPyzT4PrIqQK0pJ4wgynFFbdA1EsJQNfmdglrRQXqWtycYlPtZVgqZHTJgU6o/exec';

const ENTRY = {{
  testPerformedBy: 'entry.259274684',
  testDate:        'entry.1047488386',
  wellName:        'entry.62739910',
  runTimePct:      'entry.1380210357',
  strokesTo500:    'entry.1157762164',
  holds500:        'entry.666316702',
  pumpingPressure: 'entry.502845222',
  tagging:         'entry.1787060220',
  casingPressure:  'entry.2021631614',
  checkValve:      'entry.671821103',
  oilCut:          'entry.933783649',
  spm:             'entry.1976493259',
  notes:           'entry.1987412898',
}};

const WELLS = {wells_js};

// Set today's date
const today = new Date();
const yyyy = today.getFullYear();
const mm = String(today.getMonth() + 1).padStart(2, '0');
const dd = String(today.getDate()).padStart(2, '0');
document.getElementById('testDate').value = yyyy + '-' + mm + '-' + dd;

// Auto-fill inspector from localStorage (shared across forms)
const inspSel = document.getElementById('testPerformedBy');
const savedInspector = localStorage.getItem('fae_inspector');
if (savedInspector) inspSel.value = savedInspector;
inspSel.addEventListener('change', function() {{
  if (this.value) localStorage.setItem('fae_inspector', this.value);
}});

// Autocomplete
const wellInput = document.getElementById('wellName');
const wellListEl = document.getElementById('wellList');
const wellCountEl = document.getElementById('wellCount');
let selectedWell = '';
let activeIdx = -1;

wellInput.addEventListener('input', function() {{
  const q = this.value.toUpperCase().trim();
  selectedWell = '';
  if (q.length < 1) {{ wellListEl.style.display = 'none'; return; }}
  const matches = WELLS.filter(w => w.toUpperCase().includes(q)).slice(0, 30);
  if (matches.length === 0) {{ wellListEl.style.display = 'none'; wellCountEl.textContent = 'No matches'; return; }}
  wellCountEl.textContent = matches.length + (matches.length >= 30 ? '+' : '') + ' matches';
  activeIdx = -1;
  wellListEl.innerHTML = matches.map((w, i) => {{
    const idx = w.toUpperCase().indexOf(q);
    const hl = w.substring(0, idx) + '<mark>' + w.substring(idx, idx + q.length) + '</mark>' + w.substring(idx + q.length);
    return '<div data-idx="' + i + '" data-val="' + w.replace(/"/g, '&quot;') + '">' + hl + '</div>';
  }}).join('');
  wellListEl.style.display = 'block';
}});

wellInput.addEventListener('keydown', function(e) {{
  const items = wellListEl.querySelectorAll('div');
  if (e.key === 'ArrowDown') {{ e.preventDefault(); activeIdx = Math.min(activeIdx + 1, items.length - 1); updateActive(items); }}
  else if (e.key === 'ArrowUp') {{ e.preventDefault(); activeIdx = Math.max(activeIdx - 1, 0); updateActive(items); }}
  else if (e.key === 'Enter' && activeIdx >= 0) {{ e.preventDefault(); selectWell(items[activeIdx].dataset.val); }}
}});

function updateActive(items) {{
  items.forEach((el, i) => el.classList.toggle('active', i === activeIdx));
  if (items[activeIdx]) items[activeIdx].scrollIntoView({{ block: 'nearest' }});
}}

wellListEl.addEventListener('click', function(e) {{
  const div = e.target.closest('div[data-val]');
  if (div) selectWell(div.dataset.val);
}});

function selectWell(val) {{
  wellInput.value = val;
  selectedWell = val;
  wellListEl.style.display = 'none';
  wellCountEl.textContent = 'Selected: ' + val;
}}

document.addEventListener('click', function(e) {{
  if (!e.target.closest('.autocomplete-wrap')) wellListEl.style.display = 'none';
}});

// Numeric field validation
const NUM_FIELDS = ['runTimePct','strokesTo500','casingPressure','oilCut','spm'];
document.querySelectorAll('.num-field').forEach(inp => {{
  inp.addEventListener('input', function() {{
    const cleaned = this.value.replace(/[^0-9.]/g, '').replace(/(\\..*)\\./g, '$1');
    if (this.value !== cleaned) this.value = cleaned;
    const errEl = document.getElementById('err-' + this.id);
    if (errEl) {{ errEl.classList.remove('show'); this.classList.remove('input-error'); }}
  }});
}});

// Range field validation (e.g. "50-150")
const RANGE_FIELDS = ['pumpingPressure'];
document.querySelectorAll('.range-field').forEach(inp => {{
  inp.addEventListener('input', function() {{
    const cleaned = this.value.replace(/[^0-9.-]/g, '');
    if (this.value !== cleaned) this.value = cleaned;
    const errEl = document.getElementById('err-' + this.id);
    if (errEl) {{ errEl.classList.remove('show'); this.classList.remove('input-error'); }}
  }});
}});

function validateNums() {{
  let ok = true;
  NUM_FIELDS.forEach(id => {{
    const el = document.getElementById(id);
    if (!el || !el.value) return;
    if (!/^[0-9]*[.]?[0-9]*$/.test(el.value)) {{
      el.classList.add('input-error');
      const errEl = document.getElementById('err-' + id);
      if (errEl) errEl.classList.add('show');
      ok = false;
    }}
  }});
  RANGE_FIELDS.forEach(id => {{
    const el = document.getElementById(id);
    if (!el || !el.value) return;
    if (!/^[0-9.]+(-[0-9.]+)?$/.test(el.value.trim())) {{
      el.classList.add('input-error');
      const errEl = document.getElementById('err-' + id);
      if (errEl) errEl.classList.add('show');
      ok = false;
    }}
  }});
  return ok;
}}

// Form submission
document.getElementById('pumpup-form').addEventListener('submit', function(e) {{
  e.preventDefault();
  if (!selectedWell) {{ wellInput.focus(); wellInput.style.borderColor = '#c0392b'; return; }}
  if (!validateNums()) {{ document.querySelector('.input-error').scrollIntoView({{behavior:'smooth',block:'center'}}); return; }}

  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = 'Submitting...';

  const fd = new FormData();
  fd.append(ENTRY.testPerformedBy, document.getElementById('testPerformedBy').value);
  const dateParts = document.getElementById('testDate').value.split('-');
  fd.append(ENTRY.testDate + '_year', dateParts[0]);
  fd.append(ENTRY.testDate + '_month', dateParts[1]);
  fd.append(ENTRY.testDate + '_day', dateParts[2]);
  fd.append(ENTRY.wellName, selectedWell);

  // Radio fields
  const radios = {{holds500:'holds500', tagging:'tagging', checkValve:'checkValve'}};
  for (const [key, name] of Object.entries(radios)) {{
    const checked = document.querySelector('input[name="'+name+'"]:checked');
    if (checked) fd.append(ENTRY[key], checked.value);
  }}

  // Numeric / text fields
  const textFields = {{runTimePct:'runTimePct', strokesTo500:'strokesTo500',
    pumpingPressure:'pumpingPressure', casingPressure:'casingPressure',
    oilCut:'oilCut', spm:'spm', notes:'notes'}};
  for (const [key, id] of Object.entries(textFields)) {{
    const val = document.getElementById(id).value;
    if (val) fd.append(ENTRY[key], val);
  }}

  fetch(FORM_ACTION, {{ method: 'POST', body: fd, mode: 'no-cors' }})
    .then(() => showSuccess())
    .catch(() => showSuccess());
}});

function showSuccess() {{
  const well = selectedWell;
  const date = document.getElementById('testDate').value;
  const inspector = document.getElementById('testPerformedBy').value;
  document.getElementById('successMsg').textContent = well + ' \u2014 ' + date;
  document.getElementById('submitBtn').disabled = false;
  document.getElementById('submitBtn').textContent = 'Submit';
  document.getElementById('successOverlay').classList.add('show');
  if (photoFiles.length > 0) {{
    uploadPhotos(well, date, inspector);
  }} else {{
    document.getElementById('newEntryBtn').style.display = 'inline-block';
  }}
}}

document.getElementById('newEntryBtn').addEventListener('click', function() {{
  document.getElementById('successOverlay').classList.remove('show');
  resetForm();
}});

// Photo grid
let photoFiles = [];

document.getElementById('addPhotoBtn').addEventListener('click', function() {{
  document.getElementById('photoInput').click();
}});

document.getElementById('photoInput').addEventListener('change', function() {{
  for (const file of this.files) photoFiles.push(file);
  this.value = '';
  renderPhotoGrid();
}});

function renderPhotoGrid() {{
  const grid = document.getElementById('photoGrid');
  grid.innerHTML = '';
  photoFiles.forEach((file, i) => {{
    const thumb = document.createElement('div');
    thumb.className = 'photo-thumb';
    const img = document.createElement('img');
    img.src = URL.createObjectURL(file);
    const rm = document.createElement('button');
    rm.className = 'remove';
    rm.textContent = 'x';
    rm.type = 'button';
    rm.onclick = () => {{ photoFiles.splice(i, 1); renderPhotoGrid(); }};
    thumb.appendChild(img);
    thumb.appendChild(rm);
    grid.appendChild(thumb);
  }});
  const addBtn = document.createElement('div');
  addBtn.className = 'photo-add';
  addBtn.textContent = '+';
  addBtn.onclick = () => document.getElementById('photoInput').click();
  grid.appendChild(addBtn);
}}

function fileToBase64(file) {{
  return new Promise((resolve) => {{
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.readAsDataURL(file);
  }});
}}

async function uploadPhotos(wellSite, date, inspector) {{
  if (photoFiles.length === 0) return;
  const prog = document.getElementById('uploadProgress2');
  prog.style.display = 'block';
  const photos = [];
  for (let i = 0; i < photoFiles.length; i++) {{
    prog.textContent = 'Uploading photo ' + (i + 1) + ' of ' + photoFiles.length + '...';
    const b64 = await fileToBase64(photoFiles[i]);
    photos.push({{ name: photoFiles[i].name, base64: b64, mimeType: photoFiles[i].type || 'image/jpeg' }});
  }}
  try {{
    const resp = await fetch(PHOTO_ENDPOINT, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'text/plain' }},
      body: JSON.stringify({{ wellSite, date, inspector, photos }})
    }});
    const result = await resp.json();
    if (result.success) {{
      prog.textContent = result.count + ' photo(s) uploaded!';
    }} else {{
      prog.textContent = 'Photo upload error: ' + (result.error || '');
    }}
  }} catch (err) {{
    prog.textContent = 'Photo upload error: ' + err.message;
  }}
  document.getElementById('newEntryBtn').style.display = 'inline-block';
}}

function resetForm() {{
  document.getElementById('pumpup-form').reset();
  selectedWell = '';
  wellCountEl.textContent = '';
  photoFiles = [];
  renderPhotoGrid();
  document.getElementById('uploadProgress').style.display = 'none';
  document.getElementById('uploadProgress2').style.display = 'none';
  document.getElementById('newEntryBtn').style.display = 'none';
  // Restore inspector from localStorage
  const saved = localStorage.getItem('fae_inspector');
  if (saved) document.getElementById('testPerformedBy').value = saved;
  // Restore today's date
  document.getElementById('testDate').value = yyyy + '-' + mm + '-' + dd;
}}
</script>
</body>
</html>'''

with open('pumpup.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"pumpup.html written: {len(html)} bytes")
