const SHEET_NAME = 'Заявки';
const AUDIT_NAME = 'Аудит';
const SECRET = 'CHANGE_THIS_LONG_SECRET';

function doPost(e) {
  try {
    const data = JSON.parse(e.postData.contents || '{}');
    if (data.secret !== SECRET) return json({ok: false, error: 'forbidden'});
    const book = SpreadsheetApp.getActiveSpreadsheet();
    if (data.action === 'append_request') {
      book.getSheetByName(SHEET_NAME).appendRow(data.row || []);
      book.getSheetByName(AUDIT_NAME).appendRow([new Date(), 'Telegram bot', 'Создание заявки', data.row && data.row[0] || '', 'Записано через Apps Script']);
      return json({ok: true});
    }
    return json({ok: false, error: 'unknown_action'});
  } catch (error) {
    return json({ok: false, error: String(error)});
  }
}

function json(value) {
  return ContentService.createTextOutput(JSON.stringify(value)).setMimeType(ContentService.MimeType.JSON);
}
