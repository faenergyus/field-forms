"""Generate fap.html — Fluid Levels (FAP) form with dual photo upload."""
import json, sys

sys.path.insert(0, r"C:\Users\RSwift\.claude\skills\powerbi-query")
from pbi_helpers import get_delegated_token, execute_dax

print("Querying Operations for non-injection wells...")
token = get_delegated_token()
rows = execute_dax(token, """
EVALUATE
CALCULATETABLE(
    VALUES('Pumper Data'[Well Name]),
    'Pumper Data'[TypeX] <> "Injector"
)
ORDER BY 'Pumper Data'[Well Name]
""")
wells = sorted(set(r['Well Name'] for r in rows if r.get('Well Name')))
print(f"  {len(wells)} wells loaded from Operations (injection wells excluded)")

wells_js = json.dumps(wells)

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <title>Fluid Levels (FAP)</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f4f0; color: #1a1a1a; min-height: 100vh; }}
    .header {{ background: #1c4a1c; padding: 12px 16px; display: flex; align-items: center; gap: 12px; border-bottom: none; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 10px rgba(0,0,0,0.25); }}
    .header h1 {{ font-size: 1.1rem; color: #5dc85d; font-weight: 700; flex: 1; }}
    .container {{ max-width: 600px; margin: 0 auto; padding: 16px; }}
    .section {{ background: #fff; border-radius: 9px; padding: 16px; margin-bottom: 12px; border-left: 4px solid #3a8a3a; box-shadow: 0 1px 4px rgba(0,0,0,0.07); }}
    .section-title {{ color: #4a724a; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.12em; margin-bottom: 12px; }}
    label {{ display: block; color: #3a5a3a; font-size: 0.85rem; margin-bottom: 4px; font-weight: 500; }}
    .required::after {{ content: " *"; color: #c0392b; }}
    input[type="text"], input[type="date"], select, textarea {{
      width: 100%; padding: 9px 12px; background: #fff; border: 1.5px solid #c8ddc8;
      border-radius: 6px; color: #1a1a1a; font-size: 16px; margin-bottom: 12px;
      -webkit-appearance: none;
    }}
    input:focus, select:focus, textarea:focus {{ outline: none; border-color: #3a8a3a; box-shadow: 0 0 0 2px rgba(58,138,58,0.15); }}
    input.input-error {{ border-color: #c0392b !important; background: #fff5f5; }}
    .field-error {{ color: #c0392b; font-size: 0.75rem; margin-top: -8px; margin-bottom: 8px; display: none; }}
    .field-error.show {{ display: block; }}
    textarea {{ min-height: 80px; resize: vertical; }}
    .submit-btn {{ width: 100%; padding: 14px; background: #2d7a2d; color: #fff; border: none; border-radius: 8px; font-size: 1rem; font-weight: 600; cursor: pointer; margin-top: 8px; box-shadow: 0 2px 6px rgba(0,0,0,0.15); }}
    .submit-btn:active {{ background: #1c5a1c; }}
    .submit-btn:disabled {{ background: #8aaa8a; cursor: not-allowed; }}

    /* Autocomplete */
    .autocomplete-wrap {{ position: relative; }}
    .autocomplete-wrap input {{ margin-bottom: 0; }}
    .autocomplete-list {{ position: absolute; top: 100%; left: 0; right: 0; background: #fff; border: 1.5px solid #3a8a3a; border-top: none; border-radius: 0 0 6px 6px; max-height: 200px; overflow-y: auto; z-index: 50; display: none; box-shadow: 0 4px 12px rgba(0,0,0,0.1); }}
    .autocomplete-list div {{ padding: 10px 12px; cursor: pointer; font-size: 0.9rem; border-bottom: 1px solid #eaf5ea; color: #1a1a1a; }}
    .autocomplete-list div:hover, .autocomplete-list div.active {{ background: #eaf5ea; color: #1c4a1c; }}
    .autocomplete-list div mark {{ background: none; color: #2d7a2d; font-weight: 700; }}
    .well-count {{ font-size: 0.7rem; color: #6a8a6a; margin-top: 4px; margin-bottom: 12px; }}

    /* Success overlay */
    .overlay {{ display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6); z-index: 200; align-items: center; justify-content: center; flex-direction: column; gap: 16px; }}
    .overlay.show {{ display: flex; }}
    .overlay-card {{ background: #fff; border: 2px solid #3a8a3a; border-radius: 12px; padding: 32px; text-align: center; max-width: 340px; width: 90%; box-shadow: 0 8px 32px rgba(0,0,0,0.2); }}
    .overlay-card .checkmark {{ font-size: 3rem; margin-bottom: 8px; color: #2d7a2d; }}
    .overlay-card h2 {{ color: #1c4a1c; margin-bottom: 8px; }}
    .overlay-card p {{ color: #4a724a; font-size: 0.9rem; margin-bottom: 16px; }}
    .overlay-btn {{ padding: 12px 24px; border-radius: 8px; border: none; font-size: 0.95rem; font-weight: 600; cursor: pointer; margin: 4px; }}
    .btn-new {{ background: #2d7a2d; color: #fff; }}
    .btn-new:active {{ background: #1c5a1c; }}

    /* Photo upload */
    .photo-grid {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 8px 0 12px; }}
    .photo-thumb {{ position: relative; aspect-ratio: 1; border-radius: 6px; overflow: hidden; border: 1.5px solid #c8ddc8; }}
    .photo-thumb img {{ width: 100%; height: 100%; object-fit: cover; }}
    .photo-thumb .remove {{ position: absolute; top: 2px; right: 2px; background: rgba(0,0,0,0.55); color: #fff; border: none; border-radius: 50%; width: 22px; height: 22px; font-size: 14px; cursor: pointer; line-height: 22px; text-align: center; }}
    .photo-add {{ aspect-ratio: 1; border: 2px dashed #c8ddc8; border-radius: 6px; display: flex; align-items: center; justify-content: center; cursor: pointer; color: #8aaa8a; font-size: 2rem; background: #f5faf5; }}
    .photo-add:active {{ background: #eaf5ea; }}
    .upload-progress {{ margin-top: 4px; color: #4a724a; font-size: 0.82rem; text-align: center; }}
    .photo-label {{ font-size: 0.78rem; color: #5a7a5a; font-weight: 600; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.08em; }}
    .photo-cols {{ display: flex; gap: 12px; }}
    .photo-col {{ flex: 1; min-width: 0; }}
    .photo-col .photo-grid {{ grid-template-columns: repeat(2, 1fr); }}
  </style>
</head>
<body>
  <div class="header">
    <h1>Fluid Levels (FAP)</h1>
    <button onclick="window.close()" style="background:none;border:none;color:#90bc90;font-size:1.3rem;cursor:pointer;padding:4px 8px;line-height:1;" title="Close">&#x2715;</button>
  </div>

  <div class="container">
    <form id="fap-form" autocomplete="off">

      <div class="section">
        <div class="section-title">FAP Info</div>
        <label class="required">FAP Shot By</label>
        <select id="fapShotBy" required>
          <option value="">Select...</option>
          <option>Andy</option><option>Armando</option><option>Gary</option><option>Henry</option>
          <option>Jason</option><option>Joe</option><option>Larry</option><option>Raul</option>
          <option>Shane</option><option>Waldo</option><option>Wynn</option>
        </select>

        <label class="required">FAP Date</label>
        <input type="date" id="fapDate" required>

        <label class="required">Well Name</label>
        <div class="autocomplete-wrap">
          <input type="text" id="wellName" placeholder="Start typing well name..." required autocomplete="off">
          <div class="autocomplete-list" id="wellList"></div>
        </div>
        <div class="well-count" id="wellCount">{len(wells)} wells</div>
      </div>

      <div class="section">
        <div class="section-title">Readings</div>
        <label>FAP, ft</label>
        <input type="text" id="fap" inputmode="decimal" placeholder="e.g. 247" class="num-field">
        <div class="field-error" id="err-fap">Numbers only</div>
        <label>Runtime %</label>
        <input type="text" id="runtimePct" inputmode="decimal" placeholder="e.g. 85" class="num-field">
        <div class="field-error" id="err-runtimePct">Numbers only</div>
        <label>SPM</label>
        <input type="text" id="spm" inputmode="decimal" placeholder="e.g. 5.2" class="num-field">
        <div class="field-error" id="err-spm">Numbers only</div>
      </div>

      <div class="section">
        <div class="section-title">Notes</div>
        <label>Comment</label>
        <textarea id="comment" placeholder="Any additional observations..."></textarea>
      </div>

      <div class="section">
        <div class="section-title">Photos</div>
        <div class="photo-cols">
          <div class="photo-col">
            <div class="photo-label">Results</div>
            <div class="photo-grid" id="resultsPhotoGrid">
              <div class="photo-add" id="addResultsBtn">+</div>
            </div>
            <input type="file" id="resultsPhotoInput" accept="image/*" multiple style="display:none">
          </div>
          <div class="photo-col">
            <div class="photo-label">Wave Photo</div>
            <div class="photo-grid" id="wavePhotoGrid">
              <div class="photo-add" id="addWaveBtn">+</div>
            </div>
            <input type="file" id="wavePhotoInput" accept="image/*" multiple style="display:none">
          </div>
        </div>
      </div>

      <button type="submit" class="submit-btn" id="submitBtn">Submit FAP</button>
    </form>
  </div>

  <!-- Success overlay -->
  <div class="overlay" id="successOverlay">
    <div class="overlay-card">
      <div class="checkmark">&#10003;</div>
      <h2>Submitted!</h2>
      <p id="successMsg"></p>
      <div class="upload-progress" id="uploadProgress" style="margin-bottom:8px;"></div>
      <button class="overlay-btn btn-new" id="newFapBtn" style="display:none;">New FAP</button>
    </div>
  </div>

<script>
const FORM_ACTION = 'https://docs.google.com/forms/d/e/1FAIpQLSdCcBOip_WpdnCeAu-wqwWIjMK1mTBkr-QLZxAOnzseaJ2dOA/formResponse';
const PHOTO_ENDPOINT = 'https://script.google.com/macros/s/AKfycbwOXsEqPyzT4PrIqQK0pJ4wgynFFbdA1EsJQNfmdglrRQXqWtycYlPtZVgqZHTJgU6o/exec';

const ENTRY = {{
  fapShotBy:  'entry.535660935',
  wellName:   'entry.1765492596',
  fapDate:    'entry.602947370',
  fap:        'entry.1993995109',
  runtimePct: 'entry.363285468',
  spm:        'entry.1035988398',
  comment:    'entry.1233846332',
}};

const WELLS = {wells_js};

// Set today
const today = new Date();
const yyyy = today.getFullYear();
const mm = String(today.getMonth() + 1).padStart(2, '0');
const dd = String(today.getDate()).padStart(2, '0');
document.getElementById('fapDate').value = yyyy + '-' + mm + '-' + dd;

// Auto-fill inspector from localStorage
const inspSel = document.getElementById('fapShotBy');
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
document.querySelectorAll('.num-field').forEach(inp => {{
  inp.addEventListener('input', function() {{
    const cleaned = this.value.replace(/[^0-9.]/g, '').replace(/(\\..*)\\./g, '$1');
    if (this.value !== cleaned) this.value = cleaned;
    const errEl = document.getElementById('err-' + this.id);
    if (errEl) {{ errEl.classList.remove('show'); this.classList.remove('input-error'); }}
  }});
}});

function validateNums() {{
  let ok = true;
  ['fap', 'runtimePct', 'spm'].forEach(id => {{
    const el = document.getElementById(id);
    if (!el || !el.value) return;
    if (!/^[0-9]*[.]?[0-9]*$/.test(el.value)) {{
      el.classList.add('input-error');
      const errEl = document.getElementById('err-' + id);
      if (errEl) errEl.classList.add('show');
      ok = false;
    }}
  }});
  return ok;
}}

// Form submission
document.getElementById('fap-form').addEventListener('submit', function(e) {{
  e.preventDefault();
  if (!selectedWell) {{ wellInput.focus(); wellInput.style.borderColor = '#c0392b'; return; }}
  if (!validateNums()) {{ document.querySelector('.input-error').scrollIntoView({{behavior:'smooth',block:'center'}}); return; }}

  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = 'Submitting...';

  const fd = new FormData();
  fd.append(ENTRY.fapShotBy, document.getElementById('fapShotBy').value);
  fd.append(ENTRY.wellName, selectedWell);
  const dateParts = document.getElementById('fapDate').value.split('-');
  fd.append(ENTRY.fapDate + '_year',  dateParts[0]);
  fd.append(ENTRY.fapDate + '_month', dateParts[1]);
  fd.append(ENTRY.fapDate + '_day',   dateParts[2]);

  const texts = {{ fap:'fap', runtimePct:'runtimePct', spm:'spm', comment:'comment' }};
  for (const [key, id] of Object.entries(texts)) {{
    const val = document.getElementById(id).value;
    if (val) fd.append(ENTRY[key], val);
  }}

  fetch(FORM_ACTION, {{ method: 'POST', body: fd, mode: 'no-cors' }})
    .then(() => showSuccess())
    .catch(() => showSuccess());
}});

function showSuccess() {{
  const well = selectedWell;
  const date = document.getElementById('fapDate').value;
  const inspector = document.getElementById('fapShotBy').value;
  document.getElementById('successMsg').textContent = well + ' \u2014 ' + date;
  document.getElementById('submitBtn').disabled = false;
  document.getElementById('submitBtn').textContent = 'Submit FAP';
  document.getElementById('successOverlay').classList.add('show');
  if (resultsFiles.length > 0 || waveFiles.length > 0) {{
    uploadAllPhotos(well, date, inspector);
  }} else {{
    setTimeout(() => window.close(), 1500);
    document.getElementById('newFapBtn').style.display = 'inline-block';
  }}
}}

document.getElementById('newFapBtn').addEventListener('click', function() {{
  document.getElementById('successOverlay').classList.remove('show');
  resetForm();
}});

// ── Photo grids ──────────────────────────────────────────────────────────────
let resultsFiles = [];
let waveFiles = [];

function setupPhotoGrid(addBtnId, inputId, filesArr, gridId) {{
  document.getElementById(addBtnId).addEventListener('click', () => document.getElementById(inputId).click());
  document.getElementById(inputId).addEventListener('change', function() {{
    for (const file of this.files) filesArr.push(file);
    this.value = '';
    renderGrid(gridId, filesArr);
  }});
}}

setupPhotoGrid('addResultsBtn', 'resultsPhotoInput', resultsFiles, 'resultsPhotoGrid');
setupPhotoGrid('addWaveBtn',    'wavePhotoInput',    waveFiles,    'wavePhotoGrid');

function renderGrid(gridId, filesArr) {{
  const grid = document.getElementById(gridId);
  grid.innerHTML = '';
  filesArr.forEach((file, i) => {{
    const thumb = document.createElement('div');
    thumb.className = 'photo-thumb';
    const img = document.createElement('img');
    img.src = URL.createObjectURL(file);
    const rm = document.createElement('button');
    rm.className = 'remove';
    rm.textContent = 'x';
    rm.onclick = () => {{ filesArr.splice(i, 1); renderGrid(gridId, filesArr); }};
    thumb.appendChild(img); thumb.appendChild(rm);
    grid.appendChild(thumb);
  }});
  const addBtn = document.createElement('div');
  addBtn.className = 'photo-add';
  addBtn.textContent = '+';
  const inputId = gridId === 'resultsPhotoGrid' ? 'resultsPhotoInput' : 'wavePhotoInput';
  addBtn.onclick = () => document.getElementById(inputId).click();
  grid.appendChild(addBtn);
}}

function fileToBase64(file) {{
  return new Promise(resolve => {{
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.readAsDataURL(file);
  }});
}}

async function uploadBatch(wellSite, date, inspector, filesArr, photoType, prog) {{
  if (filesArr.length === 0) return true;
  const photos = [];
  for (let i = 0; i < filesArr.length; i++) {{
    prog.textContent = 'Uploading ' + photoType + ' ' + (i + 1) + ' of ' + filesArr.length + '...';
    photos.push({{ name: filesArr[i].name, base64: await fileToBase64(filesArr[i]), mimeType: filesArr[i].type || 'image/jpeg' }});
  }}
  try {{
    const resp = await fetch(PHOTO_ENDPOINT, {{
      method: 'POST',
      headers: {{ 'Content-Type': 'text/plain' }},
      body: JSON.stringify({{ wellSite, date, inspector, photos, photoType }})
    }});
    const result = await resp.json();
    return result.success;
  }} catch (e) {{
    prog.textContent = photoType + ' upload error: ' + e.message;
    return false;
  }}
}}

async function uploadAllPhotos(wellSite, date, inspector) {{
  const prog = document.getElementById('uploadProgress');
  prog.style.display = 'block';
  await uploadBatch(wellSite, date, inspector, resultsFiles, 'Results', prog);
  await uploadBatch(wellSite, date, inspector, waveFiles,   'Wave',    prog);
  prog.textContent = 'Photos uploaded!';
  setTimeout(() => window.close(), 1500);
  document.getElementById('newFapBtn').style.display = 'inline-block';
}}

function resetForm() {{
  document.getElementById('fap-form').reset();
  document.getElementById('fapDate').value = yyyy + '-' + mm + '-' + dd;
  const saved = localStorage.getItem('fae_inspector');
  if (saved) document.getElementById('fapShotBy').value = saved;
  selectedWell = '';
  wellInput.value = '';
  wellCountEl.textContent = '{len(wells)} wells';
  resultsFiles = [];
  waveFiles = [];
  renderGrid('resultsPhotoGrid', resultsFiles);
  renderGrid('wavePhotoGrid', waveFiles);
  window.scrollTo(0, 0);
}}
</script>
</body>
</html>'''

with open('fap.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'fap.html written: {len(html)} bytes')
