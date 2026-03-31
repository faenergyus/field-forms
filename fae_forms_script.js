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
    cols: ['Timestamp','Inspected By','Date','Well Site','Has Power?','Has PU?','PU Runs?','Has Rods?','Has Compressor?','Suction Setpts','Discharge Limits','Discharge Press','Has Tanks?','Tanks Hooked?','Tank Details','Has Separator?','Sep Liquid?','Tubing Valve','Casing Valve','Piping','Leaks Found?','Insp Method','Leaks Fixed?','Casing Press','Tubing Press','Flow Rate MCFD','Static Press','Flow Time min','Build Time min','FAP ft','Photos']
  },
  fap: {
    sheetName: 'Form Responses 1',
    cols: ['Timestamp','Shot By','Well Name','Date','FAP ft','Runtime %','SPM','Comment','Photos']
  },
  facility: {
    sheetName: 'Facility Inspection Responses',
    cols: ['Timestamp','Inspected By','Date','Facility','Stained Pad','OOS Tanks','Wind Sock','Firewall','Firewall Comments','Pump Containment','Pump Empty','Sign','Sign Comments','Thief Hatch','Trash','Trash Comments','Darts Seals','Stencilled','Leak Method','Leaks Found?','Leaks Fixed 1','Leaks Fixed 2','Valve Note','Oxygen PPM','Env Concerns','Photos']
  },
  pumpup: {
    sheetName: 'Pump Up Responses',
    cols: ['Timestamp','Performed By','Date','Well Name','Runtime %','Strokes to 500','Holds 500?','Pumping Press','Tagging?','Casing Press','Check Valve?','Oil Cut','SPM','Notes','Photos']
  },
  grounding: {
    sheetName: 'Grounding',
    cols: ['Timestamp','Pumper','Date','Well Name','Grounded?','Equip Present?','Comment','Photos']
  },
  wellsite: {
    sheetName: 'Well Inspection Report',
    cols: ['Timestamp','Well Site','Inspected By','Inspection Date','Stained Pad?','Trash and/or unused rods, tubing, or tanks on location?','Belt Guard Installed?','Well Sign Present & Correct?','Pad Clear of Brush?','Ununsed Chemical Drum or Other Equipment on Location?','Comment','Upload Photo','Oxygen Reading, PPM','Environmental Concerns','Wellhead Parts Requiring Attention (valves, hose, plugs, etc)','Injection Screen']
  }
};

// --- Field key order (matches cols after Timestamp, before Photos) ---
var FIELD_ORDER = {
  gwi:      ['inspectedBy','inspDate','wellSite','power','pumpUnit','puRun','rods','compressor','suction','dischargeLimits','dischargePressure','tanks','tanksHooked','tankDetails','separator','sepLiquid','tubingValve','casingValve','piping','leaks','inspMethod','leaksFixed','casingPressure','tubingPressure','flowRate','staticPressure','flowTime','buildTime','fap'],
  fap:      ['fapShotBy','wellName','fapDate','fap','runtimePct','spm','comment'],
  facility: ['inspectedBy','inspDate','facilityName','stainedPad','oosTanks','windSock','firewall','firewallComments','pumpContain','pumpEmpty','sign','signComments','thiefHatch','trash','trashComments','dartsSeals','stencilled','leakMethod','leaksFound','leaksFixed1','leaksFixed2','valveNote','oxygenPPM','envConcerns'],
  pumpup:   ['testPerformedBy','testDate','wellName','runTimePct','strokesTo500','holds500','pumpingPressure','tagging','casingPressure','checkValve','oilCut','spm','notes'],
  grounding:['pumper','inspDate','wellName','grounded','equipPresent','comment'],
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
    var data     = JSON.parse(e.postData.contents);
    var formType = (data.formType || '').toLowerCase();
    var fields   = data.fields  || {};
    var photos   = data.photos  || [];

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

    // Format date fields: YYYY-MM-DD → M/D/YYYY
    Object.keys(fields).forEach(function(k) {
      var v = fields[k];
      if (v && /^\d{4}-\d{2}-\d{2}$/.test(v)) {
        var parts = v.split('-');
        fields[k] = parseInt(parts[1], 10) + '/' + parseInt(parts[2], 10) + '/' + parts[0];
      }
    });

    // Build and append row (__photos__ is an inline placeholder for forms that have
    // the photo column mid-row; other forms get photos appended at the end)
    var ss    = getSpreadsheet_(formType);
    var sheet = getOrCreateTab_(ss, formType);
    var fieldOrder      = FIELD_ORDER[formType];
    var hasInlinePhotos = fieldOrder.indexOf('__photos__') >= 0;
    var row = [new Date()];
    fieldOrder.forEach(function(key) {
      if (key === '__photos__') {
        row.push(photoUrls.join('\n'));
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

function doGet(e) {
  return respond_({ status: 'FAE Field Forms handler is live', version: '2.0' });
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
