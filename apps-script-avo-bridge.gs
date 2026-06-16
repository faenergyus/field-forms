/**
 * FAE inspection-forms → AVO bridge  (queue task #522, regulatory #515)
 * ---------------------------------------------------------------------------
 * This file is REFERENCE / DEPLOY source for the shared Google Apps Script web
 * app behind all three inspection forms (gwi.html, facility.html,
 * wellsite.html). It is NOT served by GitHub Pages — it must be pasted into the
 * Apps Script project and re-deployed by hand (a headless agent cannot edit
 * Apps Script).
 *
 * Web app deployment in use by the three forms (ENDPOINT in each *.html):
 *   https://script.google.com/macros/s/AKfycbwOXsEqPyzT4PrIqQK0pJ4wgynFFbdA1EsJQNfmdglrRQXqWtycYlPtZVgqZHTJgU6o/exec
 *
 * The forms POST  { formType:'gwi'|'facility'|'wellsite', fields:{...}, photos:[...] }
 * to doPost(). After the existing handling (Google Form relay + Drive photo
 * save) succeeds, call sendAvoBridge(data.formType, data.fields) to forward the
 * AVO subset to the FAE backend bridge.
 *
 * ---------------------------------------------------------------------------
 * ONE-TIME SETUP (Apps Script editor):
 *   Project Settings ▸ Script properties ▸ Add:
 *       FORMS_AVO_TOKEN = fae_forms_avo_5d9c2e7a1b4f8063e2a9c7d4f1b60a8e
 *   (Token lives in Script Properties — NEVER inline it here or in client HTML.)
 *
 * INTEGRATION — inside doPost(e), after you parse the body and AFTER the Form
 * relay + photo save succeed, immediately before returning the success JSON:
 *
 *     var data = JSON.parse(e.postData.contents);   // already present
 *     ... existing Google Form relay + photo save ...
 *     sendAvoBridge(data.formType, data.fields);    // <-- ADD THIS LINE
 *     return ContentService.createTextOutput(JSON.stringify({success:true, ...}))
 *
 * Then: Deploy ▸ Manage deployments ▸ edit the active web app deployment ▸
 * New version ▸ Deploy. (Re-using the SAME deployment keeps the /exec URL, so
 * the forms need no change.)
 * ---------------------------------------------------------------------------
 */

/**
 * Forward the AVO subset of an inspection submission to the FAE backend.
 * Best-effort & non-blocking: every error is swallowed + logged so an
 * AVO-bridge hiccup can never block the operator's form submit.
 *
 * @param {string} formType  'gwi' | 'facility' | 'wellsite'
 * @param {Object} fields     the same `fields` object the form POSTed
 */
function sendAvoBridge(formType, fields) {
  try {
    var token = PropertiesService.getScriptProperties().getProperty('FORMS_AVO_TOKEN');
    if (!token) { Logger.log('AVO bridge: FORMS_AVO_TOKEN not set — skipping'); return; }

    var f = fields || {};

    // AVO subset shared by all three forms. "form" selects source + linkage on
    // the backend (form_gwi/form_facility/form_wellsite; Wells vs Facilities).
    var body = {
      form:            formType,            // gwi | facility | wellsite
      inspDate:        f.inspDate || '',    // optional; bridge defaults to server today
      inspectedBy:     f.inspectedBy || '', // also used as the avo_due closed_pumper
      avoOdor:         f.avoOdor || '',
      avoOdorDetail:   f.avoOdorDetail || '',
      avoNoises:       f.avoNoises || '',
      avoNoisesDetail: f.avoNoisesDetail || '',
      avoNotes:        f.avoNotes || ''
    };

    // Per-form site identity + leaks field (the bridge accepts all three leak
    // field names: gwi=leaks, facility=leaksFound, wellsite=avoLeaks).
    if (formType === 'facility') {
      body.facilityName   = f.facilityName || '';
      body.leaksFound     = f.leaksFound || '';
      body.avoLeaksDetail = f.avoLeaksDetail || '';
    } else if (formType === 'wellsite') {
      body.wellSite       = f.wellSite || '';
      body.avoLeaks       = f.avoLeaks || '';
      body.avoLeaksDetail = f.avoLeaksDetail || '';
    } else { // 'gwi'
      body.wellSite       = f.wellSite || '';
      body.leaks          = f.leaks || '';
      body.avoLeaksDetail = f.avoLeaksDetail || '';
    }

    var resp = UrlFetchApp.fetch('https://api.40ac.us/avo/from-form', {
      method: 'post',
      contentType: 'application/json',
      headers: { 'Authorization': 'Bearer ' + token },
      payload: JSON.stringify(body),
      muteHttpExceptions: true   // never throw into the operator's submit path
    });
    Logger.log('AVO bridge [' + formType + ']: HTTP ' + resp.getResponseCode() +
               ' ' + resp.getContentText());
  } catch (err) {
    // Best-effort: log and move on; the operator's submit already succeeded.
    Logger.log('AVO bridge error [' + formType + ']: ' + err);
  }
}
