"""Generate gwi.html — Gas Well Inspection form with photo upload."""
import json, sys

sys.path.insert(0, r"C:\Users\RSwift\.claude\skills\powerbi-query")
from pbi_helpers import get_delegated_token, execute_dax

print("Querying Operations for gas wells...")
token = get_delegated_token()
rows = execute_dax(token, """
EVALUATE
CALCULATETABLE(
    VALUES('Pumper Data'[Well Name]),
    'Pumper Data'[TypeX] IN {"Gas", "Gas (ex-Oil)"}
)
ORDER BY 'Pumper Data'[Well Name]
""")
wells = sorted(set(r['Well Name'] for r in rows if r.get('Well Name')))
print(f"  {len(wells)} gas wells loaded from Operations")

wells_js = json.dumps(wells)

# Pressure options 0-40
pressure_opts = ''.join(f'              <option>{i}</option>\n' for i in range(41))

html = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0">
  <title>Gas Well Inspection</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f0f4f0; color: #1a1a1a; min-height: 100vh; }}
    .header {{ background: #1c4a1c; padding: 12px 16px; display: flex; align-items: center; gap: 12px; border-bottom: none; position: sticky; top: 0; z-index: 100; box-shadow: 0 2px 10px rgba(0,0,0,0.25); }}
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
    input.input-error {{ border-color: #c0392b !important; background: #fff5f5; }}
    .field-error {{ color: #c0392b; font-size: 0.75rem; margin-top: -8px; margin-bottom: 8px; display: none; }}
    .field-error.show {{ display: block; }}
    textarea {{ min-height: 60px; resize: vertical; }}
    .radio-group {{ display: flex; gap: 8px; margin-bottom: 12px; }}
    .radio-btn {{ flex: 1; }}
    .radio-btn input {{ display: none; }}
    .radio-btn label {{ display: block; text-align: center; padding: 8px; background: #f5faf5; border: 1.5px solid #c8ddc8; border-radius: 6px; cursor: pointer; color: #3a5a3a; font-size: 0.9rem; }}
    .radio-btn input:checked + label {{ background: #eaf5ea; border-color: #3a8a3a; color: #1c4a1c; font-weight: 600; }}
    .checkbox-group {{ display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }}
    .checkbox-btn input {{ display: none; }}
    .checkbox-btn label {{ display: block; padding: 8px 12px; background: #f5faf5; border: 1.5px solid #c8ddc8; border-radius: 6px; cursor: pointer; color: #3a5a3a; font-size: 0.85rem; }}
    .checkbox-btn input:checked + label {{ background: #eaf5ea; border-color: #3a8a3a; color: #1c4a1c; font-weight: 600; }}
    .pressure-row {{ display: flex; gap: 8px; }}
    .pressure-row > div {{ flex: 1; }}
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
  </style>
</head>
<body>
  <div class="header">
    <h1>Gas Well Inspection</h1>
    <button onclick="window.close()" style="background:none;border:none;color:#90bc90;font-size:1.3rem;cursor:pointer;padding:4px 8px;line-height:1;" title="Close">&#x2715;</button>
  </div>

  <div class="container">
    <form id="gwi-form" autocomplete="off">

      <div class="section">
        <div class="section-title">Inspector Info</div>
        <label class="required">Inspected By</label>
        <select id="inspectedBy" required>
          <option value="">Select...</option>
          <option>Andy</option><option>Armando</option><option>Eli</option><option>Henry</option>
          <option>James</option><option>Jason</option><option>Joe</option><option>Leo</option>
          <option>Raul</option><option>Shane</option><option>Waldo</option><option>Wynn</option>
        </select>

        <label class="required">Inspection Date</label>
        <input type="date" id="inspDate" required>

        <label class="required">Well Site</label>
        <div class="autocomplete-wrap">
          <input type="text" id="wellSite" placeholder="Start typing well name..." required autocomplete="off">
          <div class="autocomplete-list" id="wellList"></div>
        </div>
        <div class="well-count" id="wellCount">{len(wells)} gas wells</div>
      </div>

      <div class="section">
        <div class="section-title">Equipment</div>
        <label>Has power at location?</label>
        <div class="radio-group">
          <div class="radio-btn"><input type="radio" name="power" id="power_yes" value="Yes"><label for="power_yes">Yes</label></div>
          <div class="radio-btn"><input type="radio" name="power" id="power_no" value="No"><label for="power_no">No</label></div>
        </div>
        <label>Has pumping unit?</label>
        <div class="radio-group">
          <div class="radio-btn"><input type="radio" name="pumpUnit" id="pu_yes" value="Yes"><label for="pu_yes">Yes</label></div>
          <div class="radio-btn"><input type="radio" name="pumpUnit" id="pu_no" value="No"><label for="pu_no">No</label></div>
        </div>
        <label>Will pumping unit run?</label>
        <div class="radio-group">
          <div class="radio-btn"><input type="radio" name="puRun" id="pur_yes" value="Yes"><label for="pur_yes">Yes</label></div>
          <div class="radio-btn"><input type="radio" name="puRun" id="pur_no" value="No"><label for="pur_no">No</label></div>
        </div>
        <label>Has rods in wellbore?</label>
        <div class="radio-group">
          <div class="radio-btn"><input type="radio" name="rods" id="rods_yes" value="Yes"><label for="rods_yes">Yes</label></div>
          <div class="radio-btn"><input type="radio" name="rods" id="rods_no" value="No"><label for="rods_no">No</label></div>
        </div>
        <label>Has compressor?</label>
        <div class="radio-group">
          <div class="radio-btn"><input type="radio" name="compressor" id="comp_yes" value="Yes"><label for="comp_yes">Yes</label></div>
          <div class="radio-btn"><input type="radio" name="compressor" id="comp_no" value="No"><label for="comp_no">No</label></div>
        </div>
        <label>Suction Setpoints, psi (ex. 1-5)</label>
        <input type="text" id="suction" placeholder="e.g. 1-5">
        <label>Discharge Setpoint Limits, psi (ex. 20-50)</label>
        <input type="text" id="dischargeLimits" placeholder="e.g. 20-50">
        <label>Discharge pressure while running</label>
        <input type="text" id="dischargePressure" inputmode="decimal" placeholder="e.g. 30" class="num-field">
        <div class="field-error" id="err-dischargePressure">Numbers only</div>
      </div>

      <div class="section">
        <div class="section-title">Tanks &amp; Separator</div>
        <label>Has tanks?</label>
        <div class="radio-group">
          <div class="radio-btn"><input type="radio" name="tanks" id="tanks_yes" value="Yes"><label for="tanks_yes">Yes</label></div>
          <div class="radio-btn"><input type="radio" name="tanks" id="tanks_no" value="No"><label for="tanks_no">No</label></div>
        </div>
        <label>Tanks hooked up?</label>
        <div class="radio-group">
          <div class="radio-btn"><input type="radio" name="tanksHooked" id="th_yes" value="Yes"><label for="th_yes">Yes</label></div>
          <div class="radio-btn"><input type="radio" name="tanksHooked" id="th_no" value="No"><label for="th_no">No</label></div>
        </div>
        <label>Describe tank details</label>
        <textarea id="tankDetails" placeholder="Including numbers and types"></textarea>
        <label>Has separator on site?</label>
        <div class="radio-group">
          <div class="radio-btn"><input type="radio" name="separator" id="sep_yes" value="Yes"><label for="sep_yes">Yes</label></div>
          <div class="radio-btn"><input type="radio" name="separator" id="sep_no" value="No"><label for="sep_no">No</label></div>
        </div>
        <label>Liquid in separator?</label>
        <div class="radio-group">
          <div class="radio-btn"><input type="radio" name="sepLiquid" id="sl_yes" value="Yes"><label for="sl_yes">Yes</label></div>
          <div class="radio-btn"><input type="radio" name="sepLiquid" id="sl_no" value="No"><label for="sl_no">No</label></div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">Valves &amp; Piping</div>
        <label>Tubing valve open?</label>
        <div class="radio-group">
          <div class="radio-btn"><input type="radio" name="tubingValve" id="tv_yes" value="Yes"><label for="tv_yes">Yes</label></div>
          <div class="radio-btn"><input type="radio" name="tubingValve" id="tv_no" value="No"><label for="tv_no">No</label></div>
        </div>
        <label>Casing valve open?</label>
        <div class="radio-group">
          <div class="radio-btn"><input type="radio" name="casingValve" id="cv_yes" value="Yes"><label for="cv_yes">Yes</label></div>
          <div class="radio-btn"><input type="radio" name="casingValve" id="cv_no" value="No"><label for="cv_no">No</label></div>
        </div>
        <label>Describe piping</label>
        <textarea id="piping" placeholder="e.g. casing to compressor to meter"></textarea>
      </div>

      <div class="section">
        <div class="section-title">Leak Inspection</div>
        <label>Leaks found?</label>
        <div class="radio-group">
          <div class="radio-btn"><input type="radio" name="leaks" id="leaks_yes" value="Yes"><label for="leaks_yes">Yes</label></div>
          <div class="radio-btn"><input type="radio" name="leaks" id="leaks_no" value="No"><label for="leaks_no">No</label></div>
        </div>
        <label>Inspection Method</label>
        <div class="checkbox-group">
          <div class="checkbox-btn"><input type="checkbox" id="im_avo" value="AVO Only"><label for="im_avo">AVO Only</label></div>
          <div class="checkbox-btn"><input type="checkbox" id="im_sonic" value="AVO w/ Sonic Camera"><label for="im_sonic">AVO w/ Sonic Camera</label></div>
          <div class="checkbox-btn"><input type="checkbox" id="im_none" value="None"><label for="im_none">None</label></div>
        </div>
        <label>Leaks fixed?</label>
        <div class="radio-group">
          <div class="radio-btn"><input type="radio" name="leaksFixed" id="lf_yes" value="Yes"><label for="lf_yes">Yes</label></div>
          <div class="radio-btn"><input type="radio" name="leaksFixed" id="lf_no" value="No"><label for="lf_no">No</label></div>
        </div>
      </div>

      <div class="section">
        <div class="section-title">Readings</div>
        <div class="pressure-row">
          <div>
            <label>Casing Pressure (psi)</label>
            <select id="casingPressure">
              <option value="">--</option>
{pressure_opts}            </select>
          </div>
          <div>
            <label>Tubing Pressure (psi)</label>
            <select id="tubingPressure">
              <option value="">--</option>
{pressure_opts}            </select>
          </div>
        </div>
        <label>Flow Rate, MCFD</label>
        <input type="text" id="flowRate" inputmode="decimal" placeholder="e.g. 30" class="num-field">
        <div class="field-error" id="err-flowRate">Numbers only</div>
        <label>Static Pressure @ Meter, psi</label>
        <input type="text" id="staticPressure" inputmode="decimal" placeholder="e.g. 38" class="num-field">
        <div class="field-error" id="err-staticPressure">Numbers only</div>
        <label>How long does well flow? (minutes)</label>
        <input type="text" id="flowTime" inputmode="decimal" class="num-field">
        <div class="field-error" id="err-flowTime">Numbers only</div>
        <label>How long to build pressure to flow? (minutes)</label>
        <input type="text" id="buildTime" inputmode="decimal" class="num-field">
        <div class="field-error" id="err-buildTime">Numbers only</div>
        <label>FAP, ft</label>
        <input type="text" id="fap" inputmode="decimal" placeholder="e.g. 247" class="num-field">
        <div class="field-error" id="err-fap">Numbers only</div>
      </div>

      <!-- Photo upload section -->
      <div class="section">
        <div class="section-title">Upload Photos</div>
        <div class="photo-grid" id="photoGrid">
          <div class="photo-add" id="addPhotoBtn">+</div>
        </div>
        <input type="file" id="photoInput" accept="image/*" multiple style="display:none">
      </div>

      <button type="submit" class="submit-btn" id="submitBtn">Submit Inspection</button>
    </form>
  </div>

  <!-- Success overlay -->
  <div class="overlay" id="successOverlay">
    <div class="overlay-card">
      <div class="checkmark">&#10003;</div>
      <h2>Submitted!</h2>
      <p id="successMsg"></p>
      <div class="upload-progress" id="uploadProgress" style="margin-bottom:8px;"></div>
      <button class="overlay-btn btn-new" id="newInspBtn" style="display:none;">New Inspection</button>
    </div>
  </div>

<script>
const FORM_ACTION = 'https://docs.google.com/forms/d/e/1FAIpQLSfCoQ4xKJDhmmVBGTMgQjtQ11NgBLk4qMBuVJGHDHkmWbQxgw/formResponse';
const PHOTO_ENDPOINT = 'https://script.google.com/macros/s/AKfycbwOXsEqPyzT4PrIqQK0pJ4wgynFFbdA1EsJQNfmdglrRQXqWtycYlPtZVgqZHTJgU6o/exec';

const ENTRY = {{
  inspectedBy:      'entry.422563114',
  inspDate:         'entry.2090668001',
  wellSite:         'entry.1780066001',
  power:            'entry.1472989205',
  pumpUnit:         'entry.1524884919',
  puRun:            'entry.1907704228',
  rods:             'entry.922602014',
  compressor:       'entry.392525147',
  suction:          'entry.772623079',
  dischargeLimits:  'entry.1945323308',
  dischargePressure:'entry.532219079',
  tanks:            'entry.1170913031',
  tanksHooked:      'entry.1735293470',
  tankDetails:      'entry.1384051628',
  separator:        'entry.1912320872',
  sepLiquid:        'entry.1012083414',
  tubingValve:      'entry.2138299979',
  casingValve:      'entry.141045717',
  piping:           'entry.1697854955',
  leaks:            'entry.1702870418',
  inspMethod:       'entry.273907609',
  leaksFixed:       'entry.1987844996',
  casingPressure:   'entry.1556750364',
  tubingPressure:   'entry.71567246',
  flowRate:         'entry.1559467040',
  staticPressure:   'entry.625787921',
  flowTime:         'entry.1292265876',
  buildTime:        'entry.1602054405',
  fap:              'entry.748675123'
}};

const WELLS = {wells_js};

// Set today
const today = new Date();
const yyyy = today.getFullYear();
const mm = String(today.getMonth() + 1).padStart(2, '0');
const dd = String(today.getDate()).padStart(2, '0');
document.getElementById('inspDate').value = yyyy + '-' + mm + '-' + dd;

// Autocomplete
const wellInput = document.getElementById('wellSite');
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

// Numeric field validation — strip non-numeric on input, flag on submit
const NUM_FIELDS = ['flowRate','staticPressure','flowTime','buildTime','fap','dischargePressure'];
document.querySelectorAll('.num-field').forEach(inp => {{
  inp.addEventListener('input', function() {{
    // Allow digits and one decimal point only
    const cleaned = this.value.replace(/[^0-9.]/g, '').replace(/(\..*)\./g, '$1');
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
  return ok;
}}

// Form submission
document.getElementById('gwi-form').addEventListener('submit', function(e) {{
  e.preventDefault();
  if (!selectedWell) {{ wellInput.focus(); wellInput.style.borderColor = '#c0392b'; return; }}
  if (!validateNums()) {{ document.querySelector('.input-error').scrollIntoView({{behavior:'smooth',block:'center'}}); return; }}

  const btn = document.getElementById('submitBtn');
  btn.disabled = true;
  btn.textContent = 'Submitting...';

  const fd = new FormData();
  fd.append(ENTRY.inspectedBy, document.getElementById('inspectedBy').value);
  const dateParts = document.getElementById('inspDate').value.split('-');
  fd.append(ENTRY.inspDate + '_year', dateParts[0]);
  fd.append(ENTRY.inspDate + '_month', dateParts[1]);
  fd.append(ENTRY.inspDate + '_day', dateParts[2]);
  fd.append(ENTRY.wellSite, selectedWell);

  const radios = {{power:'power',pumpUnit:'pumpUnit',puRun:'puRun',rods:'rods',compressor:'compressor',
    tanks:'tanks',tanksHooked:'tanksHooked',separator:'separator',sepLiquid:'sepLiquid',
    tubingValve:'tubingValve',casingValve:'casingValve',leaks:'leaks',leaksFixed:'leaksFixed'}};
  for (const [key, name] of Object.entries(radios)) {{
    const checked = document.querySelector('input[name="'+name+'"]:checked');
    if (checked) fd.append(ENTRY[key], checked.value);
  }}

  document.querySelectorAll('.checkbox-group input:checked').forEach(cb => {{
    fd.append(ENTRY.inspMethod, cb.value);
  }});

  const texts = {{suction:'suction',dischargeLimits:'dischargeLimits',dischargePressure:'dischargePressure',
    tankDetails:'tankDetails',piping:'piping',flowRate:'flowRate',staticPressure:'staticPressure',
    flowTime:'flowTime',buildTime:'buildTime',fap:'fap'}};
  for (const [key, id] of Object.entries(texts)) {{
    const val = document.getElementById(id).value;
    if (val) fd.append(ENTRY[key], val);
  }}

  const cp = document.getElementById('casingPressure').value;
  const tp = document.getElementById('tubingPressure').value;
  if (cp) fd.append(ENTRY.casingPressure, cp);
  if (tp) fd.append(ENTRY.tubingPressure, tp);

  fetch(FORM_ACTION, {{ method: 'POST', body: fd, mode: 'no-cors' }})
    .then(() => showSuccess())
    .catch(() => showSuccess());
}});

function showSuccess() {{
  const well = selectedWell;
  const date = document.getElementById('inspDate').value;
  const inspector = document.getElementById('inspectedBy').value;
  document.getElementById('successMsg').textContent = well + ' \u2014 ' + date;
  document.getElementById('submitBtn').disabled = false;
  document.getElementById('submitBtn').textContent = 'Submit Inspection';
  document.getElementById('successOverlay').classList.add('show');
  if (photoFiles.length > 0) {{
    uploadPhotos(well, date, inspector);
  }} else {{
    // No photos — close after a brief moment
    setTimeout(() => window.close(), 1500);
    document.getElementById('newInspBtn').style.display = 'inline-block';
  }}
}}

document.getElementById('newInspBtn').addEventListener('click', function() {{
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
    if (result.success) {{
      prog.textContent = result.count + ' photo(s) uploaded!';
      setTimeout(() => window.close(), 1500);
    }} else {{
      prog.textContent = 'Photo upload error: ' + (result.error || '');
    }}
  }} catch (err) {{
    prog.textContent = 'Photo upload error: ' + err.message;
  }}
  document.getElementById('newInspBtn').style.display = 'inline-block';
}}

function resetForm() {{
  document.getElementById('gwi-form').reset();
  document.getElementById('inspDate').value = yyyy + '-' + mm + '-' + dd;
  selectedWell = '';
  wellInput.value = '';
  wellCountEl.textContent = '{len(wells)} gas wells';
  photoFiles = [];
  renderPhotoGrid();
  window.scrollTo(0, 0);
}}
</script>
</body>
</html>'''

with open('gwi.html', 'w', encoding='utf-8') as f:
    f.write(html)

print(f'gwi.html written: {len(html)} bytes')
