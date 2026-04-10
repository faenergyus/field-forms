// FAE Field Forms - Centralized Handler v2.0
// Handles all 6 field form types: gwi, fap, facility, pumpup, grounding, wellsite
// Writes to Google Sheets, saves photos to Drive, returns JSON response.
// Deploy as Web App: Execute as Me, Anyone can access.

// --- Config ---
// Spreadsheet IDs per form type (must already exist)
var SHEET_IDS = {
  gwi:      '1uICvI9zAz9Ai4Snpcee54RoDg0v-rYPoqylsZvs4p60',
  fap:      '146yuHYjs3RF3wtCK3Qj9NXH94DrStwhieTGqPeLQRfA',
  facility: '146yuHYjs3RF3wtCK3Qj9NXH94DrStwhieTGqPeLQRfA',
  pumpup:   '146yuHYjs3RF3wtCK3Qj9NXH94DrStwhieTGqPeLQRfA',
  grounding:'146yuHYjs3RF3wtCK3Qj9NXH94DrStwhieTGqPeLQRfA',
  wellsite: '146yuHYjs3RF3wtCK3Qj9NXH94DrStwhieTGqPeLQRfA'
};

var DRIVE_FOLDER_NAME = 'FAE Field Forms Photos';

// --- Tab names and column headers per form type ---
var FORM_CONFIGS = {
  gwi: {
    sheetName: 'Gas Well Inspection',
    cols: ['Timestamp','Inspected By','Inspection Date','Well Site','Upload Photos','Has Power?','Has PU?','Has Rods?','PU Runs?','Has Compressor?','Suction Setpts','Discharge Limits','Discharge Press','Has Tanks?','Tanks Hooked?','Tank Details','Tubing Valve','Casing Valve','Piping','Casing Press','Tubing Press','Flow Rate MCFD','Static Press','Flow Time min','Build Time min','Leaks Found?','Sonic Camera?','Insp Method','Has Separator?','Sep Liquid?','FAP ft','Leaks Fixed?']
  },
  fap: {
    sheetName: 'Form Responses 1',
    cols: ['Timestamp','Date','Well Name','FAP','Runtime %','Comment','SPM','FAP Date','Photo Upload','FAP Shot By','Engineer Comment','Wave Photo']
  },
  facility: {
    sheetName: 'Facility Inspection Responses',
    cols: ['Timestamp','Inspected By','Date','Facility','Stained Pad','OOS Tanks','Wind Sock','Firewall','Firewall Comments','Pump Containment','Pump Empty','Sign','Sign Comments','Thief Hatch','Trash','Trash Comments','Darts Seals','Stencilled','Leak Method','Leaks Found?','Leaks Fixed 1','Leaks Fixed 2','Valve Note','Oxygen PPM','Env Concerns','Photos']
  },
  pumpup: {
    sheetName: 'Pump Up Responses',
    cols: ['Timestamp','Well Name','Runtime %','Strokes to 500','Holds 500?','','Pumping Press','Tagging?','Casing Press','Oil Cut','SPM','Notes','Test Date','Performed By','Photos','Additional Photo','Check Valve?']
  },
  grounding: {
    sheetName: 'Grounding',
    cols: ['Timestamp','Pumper','','Well Name','Inspection Date','Is Grounded?','Grounding equipment present?','Comment','Photos']
  },
  wellsite: {
    sheetName: 'Well Inspection Report',
    cols: ['Timestamp','Well Site','Inspected By','Inspection Date','Stained Pad?','Trash and/or unused rods, tubing, or tanks on location?','Belt Guard Installed?','Well Sign Present & Correct?','Pad Clear of Brush?','Ununsed Chemical Drum or Other Equipment on Location?','Comment','Upload Photo','Oxygen Reading, PPM','Environmental Concerns','Wellhead Parts Requiring Attention (valves, hose, plugs, etc)','Injection Screen']
  }
};

// --- Field key order (matches cols after Timestamp, before Photos) ---
var FIELD_ORDER = {
  gwi:      ['inspectedBy','inspDate','wellSite','__photos__','power','pumpUnit','rods','puRun','compressor','suction','dischargeLimits','dischargePressure','tanks','tanksHooked','tankDetails','tubingValve','casingValve','piping','casingPressure','tubingPressure','flowRate','staticPressure','flowTime','buildTime','leaks','','inspMethod','separator','sepLiquid','fap','leaksFixed'],
  fap:      ['fapDate','wellName','fap','runtimePct','comment','spm','fapDate','__photos_results__','fapShotBy','engineerComment','__photos_wave__'],
  facility: ['inspectedBy','inspDate','facilityName','stainedPad','oosTanks','windSock','firewall','firewallComments','pumpContain','pumpEmpty','sign','signComments','thiefHatch','trash','trashComments','dartsSeals','stencilled','','oxygenPPM','valveNote','leakMethod','leaksFound','leaksFixed1','leaksFixed2','envConcerns'],
  pumpup:   ['wellName','runTimePct','strokesTo500','holds500','','pumpingPressure','tagging','casingPressure','oilCut','spm','notes','testDate','testPerformedBy','__photos__','','checkValve'],
  grounding:['pumper','','wellName','inspDate','grounded','equipPresent','comment'],
  wellsite: ['wellSite','inspectedBy','inspDate','stainedPad','trash','beltGuard','wellSign','padBrush','unusedEquip','comment','__photos__','oxygenPPM','envConcerns','wellheadParts','injectionScreen']
};

// --- Spreadsheet helpers ---
function getSpreadsheet_(formType) {
  var id = SHEET_IDS[formType];
  return SpreadsheetApp.openById(id);
}

function getOrCreateTab_(ss, formType) {
  var cfg = FORM_CONFIGS[formType];
  if (!cfg) return null;
  var sheet = ss.getSheetByName(cfg.sheetName);
  if (!sheet) {
    sheet = ss.insertSheet(cfg.sheetName);
    sheet.appendRow(cfg.cols);
    var hdr = sheet.getRange(1, 1, 1, cfg.cols.length);
    hdr.setFontWeight('bold').setBackground('#1a5276').setFontColor('#ffffff');
    sheet.setFrozenRows(1);
  }
  return sheet;
}

function getOrCreatePhotoFolder_(formType) {
  var cfg = FORM_CONFIGS[formType];
  var childName = (cfg ? cfg.sheetName : formType) + ' Photos';
  var parents = DriveApp.getFoldersByName(DRIVE_FOLDER_NAME);
  var parent = parents.hasNext() ? parents.next() : DriveApp.createFolder(DRIVE_FOLDER_NAME);
  var children = parent.getFoldersByName(childName);
  return children.hasNext() ? children.next() : parent.createFolder(childName);
}

// --- Web app entry points ---
function doPost(e) {
  try {
    var data       = JSON.parse(e.postData.contents);
    var formType   = (data.formType || '').toLowerCase();
    var fields     = data.fields     || {};
    var photos     = data.photos     || [];
    var wavePhotos = data.wavePhotos || [];

    if (!FORM_CONFIGS[formType]) {
      return respond_({ error: 'Unknown formType: ' + formType });
    }

    // Upload photos to Drive
    var folder    = getOrCreatePhotoFolder_(formType);
    var photoUrls = [];
    photos.forEach(function(p) {
      var blob = Utilities.newBlob(
        Utilities.base64Decode(p.base64),
        p.mimeType || 'image/jpeg',
        p.name || ('photo_' + Date.now() + '.jpg')
      );
      var file = folder.createFile(blob);
      file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
      photoUrls.push('https://drive.google.com/open?id=' + file.getId());
    });

    var wavePhotoUrls = [];
    wavePhotos.forEach(function(p) {
      var blob = Utilities.newBlob(
        Utilities.base64Decode(p.base64),
        p.mimeType || 'image/jpeg',
        p.name || ('wave_' + Date.now() + '.jpg')
      );
      var file = folder.createFile(blob);
      file.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
      wavePhotoUrls.push('https://drive.google.com/open?id=' + file.getId());
    });

    // Format date fields: YYYY-MM-DD → M/D/YYYY
    Object.keys(fields).forEach(function(k) {
      var v = fields[k];
      if (v && /^\d{4}-\d{2}-\d{2}$/.test(v)) {
        var parts = v.split('-');
        fields[k] = parseInt(parts[1], 10) + '/' + parseInt(parts[2], 10) + '/' + parts[0];
      }
    });

    // Build and append row.
    // __photos_results__ and __photos_wave__ are inline placeholders for forms that
    // have photo columns mid-row; __photos__ (legacy) also maps to results photos.
    // Forms without any inline placeholder get photos appended at the end.
    var ss    = getSpreadsheet_(formType);
    var sheet = getOrCreateTab_(ss, formType);
    var fieldOrder      = FIELD_ORDER[formType];
    var hasInlinePhotos = fieldOrder.some(function(k) {
      return k === '__photos__' || k === '__photos_results__' || k === '__photos_wave__';
    });
    var row = [new Date()];
    fieldOrder.forEach(function(key) {
      if (key === '__photos__' || key === '__photos_results__') {
        row.push(photoUrls.join('\n'));
      } else if (key === '__photos_wave__') {
        row.push(wavePhotoUrls.join('\n'));
      } else {
        row.push(fields[key] !== undefined ? fields[key] : '');
      }
    });
    if (!hasInlinePhotos) {
      row.push(photoUrls.join('\n'));
    }
    sheet.appendRow(row);

    return respond_({ success: true, photoUrls: photoUrls, sheetUrl: ss.getUrl() });

  } catch(err) {
    return respond_({ error: err.message });
  }
}

// --- Spare Vessels sheet config ---
var SV_SHEET_ID   = '146yuHYjs3RF3wtCK3Qj9NXH94DrStwhieTGqPeLQRfA';
var SV_TAB        = 'Spare Vessels';
var SV_COL_TS     = 1;   // Timestamp
var SV_COL_LOC    = 2;   // Location
var SV_COL_HT     = 3;   // Height (ft)
var SV_COL_DIA    = 4;   // Diameter (in)
var SV_COL_PHOTO  = 5;   // Upload 1 picture
var SV_COL_LAT    = 7;   // Latitude
var SV_COL_LNG    = 8;   // Longitude
var SV_COL_REP    = 10;  // Reporter
var SV_COL_USED   = 11;  // Picked Up

function doGet(e) {
  var params = e ? (e.parameter || {}) : {};
  try {
    if (params.report === 'spareVessels') { return getSpareVessels_(); }
    if (params.action === 'setUsed')      { return setSpareVesselUsed_(parseInt(params.row, 10), params.used === '1'); }
    return respond_({ status: 'FAE Field Forms handler is live', version: '2.0' });
  } catch(err) {
    return respond_({ error: err.message });
  }
}

function getSpareVessels_() {
  var ss    = SpreadsheetApp.openById(SV_SHEET_ID);
  var sheet = ss.getSheetByName(SV_TAB);
  if (!sheet) return respond_({ error: 'Spare Vessels sheet not found' });
  var lastRow = sheet.getLastRow();
  if (lastRow < 2) return respond_({ rows: [] });
  var data = sheet.getRange(2, 1, lastRow - 1, SV_COL_USED).getValues();
  var rows = [];
  data.forEach(function(row, i) {
    var photoUrl = row[SV_COL_PHOTO - 1] || '';
    var m = photoUrl.match(/[?&]id=([^&]+)/);
    var fileId   = m ? m[1] : '';
    var thumbUrl = fileId ? 'https://drive.google.com/thumbnail?id=' + fileId + '&sz=w200' : '';
    var ts = row[SV_COL_TS - 1];
    var tsStr = ts instanceof Date
      ? Utilities.formatDate(ts, 'America/Chicago', 'M/d/yyyy h:mm a')
      : String(ts || '');
    rows.push({
      rowNum:    i + 2,
      timestamp: tsStr,
      location:  String(row[SV_COL_LOC  - 1] || ''),
      height:    String(row[SV_COL_HT   - 1] || ''),
      diameter:  String(row[SV_COL_DIA  - 1] || ''),
      photoUrl:  photoUrl,
      thumbUrl:  thumbUrl,
      lat:       String(row[SV_COL_LAT  - 1] || ''),
      lng:       String(row[SV_COL_LNG  - 1] || ''),
      reporter:  String(row[SV_COL_REP  - 1] || ''),
      used:      !!(row[SV_COL_USED - 1])
    });
  });
  return respond_({ rows: rows });
}

function setSpareVesselUsed_(row, used) {
  if (!row || row < 2) return respond_({ error: 'Invalid row' });
  var ss    = SpreadsheetApp.openById(SV_SHEET_ID);
  var sheet = ss.getSheetByName(SV_TAB);
  if (!sheet) return respond_({ error: 'Spare Vessels sheet not found' });
  sheet.getRange(row, SV_COL_USED).setValue(used ? 'Yes' : '');
  return respond_({ success: true });
}

function respond_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj))
    .setMimeType(ContentService.MimeType.JSON);
}

// --- Test: logs sheet URLs for all form types ---
function printSheetUrls() {
  Object.keys(SHEET_IDS).forEach(function(ft) {
    var ss = getSpreadsheet_(ft);
    Logger.log(ft + ': ' + ss.getUrl());
  });
}
