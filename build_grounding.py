"""Generate grounding.html — Wellhead Grounding Survey form with photo upload."""
import json, sys

sys.path.insert(0, r"C:\Users\RSwift\.claude\skills\powerbi-query")
from pbi_helpers import get_delegated_token, execute_dax

print("Querying Operations for all wells...")
token = get_delegated_token()
rows = execute_dax(token, """
EVALUATE
VALUES('Pumper Data'[Well Name])
ORDER BY 'Pumper Data'[Well Name]
""")
wells = sorted(set(r['Well Name'] for r in rows if r.get('Well Name')))
print(f"  {len(wells)} wells loaded from Operations")

wells_js = json.dumps(wells)

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <title>Wellhead Grounding Survey</title>
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
    input[type="text"], input[type="date"], select, textarea {{
      width: 100%; padding: 9px 12px; background: #fff; border: 1.5px solid #c8ddc8;
      border-radius: 6px; color: #1a1a1a; font-size: 16px; margin-bottom: 12px;
      -webkit-appearance: none;
    }}
    input:focus, select:focus, textarea:focus {{ outline: none; border-color: #3a8a3a; box-shadow: 0 0 0 2px rgba(58,138,58,0.15); }}
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
    .upload-progress {{ font-size: 0.85rem; color: #3a5a3a; margin-bottom: 12px; display: none; }}
    .overlay-btn {{ padding: 10px 24px; border: none; border-radius: 8px; font-size: 0.95rem; font-weight: 600; cursor: pointer; }}
    .btn-new {{ background: #2d7a2d; color: #fff; }}
  </style>
</head>
<body>

<div class="header">
  <h1>⚡ Wellhead Grounding Survey</h1>
  <a href="index.html">← Portal</a>
</div>

<div class="container">
  <form id="grounding-form">

    <!-- Survey Info -->
    <div class="section">
      <div class="section-title">Survey Info</div>

      <label class="required" for="pumper">Pumper</label>
      <select id="pumper" required>
        <option value="">Select pumper...</option>
        <option>Andy</option>
        <option>Armando</option>
        <option>Gary</option>
        <option>Henry</option>
        <option>Jason</option>
        <option>Joe</option>
        <option>Larry</option>
        <option>Raul</option>
        <option>Shane</option>
        <option>Waldo</option>
        <option>Wynn</option>
      </select>

      <label class="required" for="inspDate">Inspection Date</label>
      <input type="date" id="inspDate" required>

      <label class="required" for="wellName">Well Name</label>
      <div class="autocomplete-wrap">
        <input type="text" id="wellName" placeholder="Type to search wells..." autocomplete="off" required>
        <div class="autocomplete-list" id="wellList"></div>
      </div>
      <div class="well-count" id="wellCount"></div>
    </div>

    <!-- Grounding Status -->
    <div class="section">
      <div class="section-title">Grounding Status</div>

      <label class="required">Is well CURRENTLY grounded?</label>
      <div class="radio-group">
        <div class="radio-btn"><input type="radio" name="grounded" id="grounded-yes" value="Yes"><label for="grounded-yes">Yes</label></div>
        <div class="radio-btn"><input type="radio" name="grounded" id="grounded-no" value="No"><label for="grounded-no">No</label></div>
      </div>

      <label class="required">Grounding equipment present?</label>
      <div class="radio-group">
        <div class="radio-btn"><input type="radio" name="equipPresent" id="equip-yes" value="Yes"><label for="equip-yes">Yes</label></div>
        <div class="radio-btn"><input type="radio" name="equipPresent" id="equip-no" value="No"><label for="equip-no">No</label></div>
        <div class="radio-btn"><input type="radio" name="equipPresent" id="equip-grounded" value="Is Grounded"><label for="equip-grounded">Is Grounded</label></div>
      </div>
    </div>

    <!-- Comment -->
    <div class="section">
      <div class="section-title">Comment</div>
      <label for="comment">Comment</label>
      <textarea id="comment" placeholder="Any additional notes..."></textarea>
    </div>

    <!-- Photo -->
    <div class="section">
      <div class="section-title">Photo</div>
      <input type="file" id="photoInput" accept="image/*" multiple style="display:none">
      <div class="photo-grid" id="photoGrid">
        <div class="photo-add" id="addPhotoBtn">+</div>
      </div>
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
    <div class="upload-progress" id="uploadProgress"></div>
    <button class="overlay-btn btn-new" id="newSurveyBtn" style="display:none;">New Survey</button>
  </div>
</div>

<script>
const FORM_ACTION = 'https://docs.google.com/forms/d/e/1FAIpQLScfajrcfmHWPTQXIcRwiD4PH0oXe1rcyPMmRF_LIN_k80Ut0Q/formResponse';
const PHOTO_ENDPOINT = 'https://script.google.com/macros/s/AKfycbwOXsEqPyzT4PrIqQK0pJ4wgynFFbdA1EsJQNfmdglrRQXqWtycYlPtZVgqZHTJgU6o/exec';

const ENTRY = {{
  pumper:       'entry.1919110646',
  inspDate:     'entry.1468126586',
  wellName:     'entry.1968423832',
  grounded:     'entry.987622576',
  equipPresent: 'entry.2089025970',
  comment:      'entry.1682788240',
}};

const WELLS = {wells_js};

// Set today's date
const today = new Date();
const yyyy = today.getFullYear();
const mm = String(today.getMonth() + 1).padStart(2, '0');
const dd = String(today.getDate()).padStart(2, '0');
document.getElementById('inspDate').value = yyyy + '-' + mm + '-' + dd;

// Auto-fill inspector from localStorage
const pumperSel = document.getElementById('pumper');
const savedInspector = localStorage.getItem('fae_inspector');
if (savedInspector) pumperSel.value = savedInspector;
pumperSel.addEventListener('change', function() {{
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

// Form submission
document.getElementById('grounding-form').addEventListener('submit', function(e) {{
  e.preventDefault();
  if (!selectedWell) {{ wellInput.focus(); wellInput.style.borderColor = '#c0392b'; return; }}

  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = 'Submitting...';

  const fd = new FormData();
  fd.append(ENTRY.pumper, document.getElementById('pumper').value);
  const dateParts = document.getElementById('inspDate').value.split('-');
  fd.append(ENTRY.inspDate + '_year', dateParts[0]);
  fd.append(ENTRY.inspDate + '_month', dateParts[1]);
  fd.append(ENTRY.inspDate + '_day', dateParts[2]);
  fd.append(ENTRY.wellName, selectedWell);

  const grounded = document.querySelector('input[name="grounded"]:checked');
  if (grounded) fd.append(ENTRY.grounded, grounded.value);

  const equip = document.querySelector('input[name="equipPresent"]:checked');
  if (equip) fd.append(ENTRY.equipPresent, equip.value);

  const comment = document.getElementById('comment').value;
  if (comment) fd.append(ENTRY.comment, comment);

  fetch(FORM_ACTION, {{ method: 'POST', body: fd, mode: 'no-cors' }})
    .then(() => showSuccess())
    .catch(() => showSuccess());
}});

function showSuccess() {{
  const well = selectedWell;
  const date = document.getElementById('inspDate').value;
  const inspector = document.getElementById('pumper').value;
  document.getElementById('successMsg').textContent = well + ' \u2014 ' + date;
  document.getElementById('submitBtn').disabled = false;
  document.getElementById('submitBtn').textContent = 'Submit';
  document.getElementById('successOverlay').classList.add('show');
  if (photoFiles.length > 0) {{
    uploadPhotos(well, date, inspector);
  }} else {{
    document.getElementById('newSurveyBtn').style.display = 'inline-block';
  }}
}}

document.getElementById('newSurveyBtn').addEventListener('click', function() {{
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
  const prog = document.getElementById('uploadProgress');
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
    prog.textContent = result.success ? result.count + ' photo(s) uploaded!' : 'Upload error: ' + (result.error || '');
  }} catch (err) {{
    prog.textContent = 'Upload error: ' + err.message;
  }}
  document.getElementById('newSurveyBtn').style.display = 'inline-block';
}}

function resetForm() {{
  document.getElementById('grounding-form').reset();
  selectedWell = '';
  wellCountEl.textContent = '';
  photoFiles = [];
  renderPhotoGrid();
  document.getElementById('uploadProgress').style.display = 'none';
  document.getElementById('newSurveyBtn').style.display = 'none';
  const saved = localStorage.getItem('fae_inspector');
  if (saved) document.getElementById('pumper').value = saved;
  document.getElementById('inspDate').value = yyyy + '-' + mm + '-' + dd;
}}
</script>
</body>
</html>'''

with open('grounding.html', 'w', encoding='utf-8') as f:
    f.write(html)
print(f"grounding.html written: {len(html)} bytes")
