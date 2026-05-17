/**
 * AutoMind Beauty Hub CRM Automation
 * Этот скрипт помогает автоматизировать сегментацию и расчеты в Google Таблице.
 */

function onEdit(e) {
  const sheet = e.source.getActiveSheet();
  const range = e.range;

  // 1. Авто-обновление даты последнего визита при изменении статуса на "Завершен"
  if (sheet.getName() === "Клиенты" && range.getColumn() === 6) { // Столбец "Статус последней записи"
    const status = range.getValue();
    if (status === "Завершен") {
      const row = range.getRow();
      sheet.getRange(row, 7).setValue(new Date()); // Записываем дату в столбец "Дата последнего визита"
    }
  }
}

/**
 * Создает меню в интерфейсе таблицы
 */
function onOpen() {
  const ui = SpreadsheetApp.getUi();
  ui.createMenu('🚀 AutoMind AI')
      .addItem('Обновить сегментацию', 'updateSegmentation')
      .addItem('Рассчитать LTV', 'calculateLTV')
      .addToUi();
}

/**
 * Пример функции для обновления сегментации (спящие клиенты и т.д.)
 */
function updateSegmentation() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Клиенты");
  const data = sheet.getDataRange().getValues();
  const today = new Date();

  for (let i = 1; i < data.length; i++) {
    const lastVisit = new Date(data[i][6]); // 7-й столбец G
    const diffTime = Math.abs(today - lastVisit);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    let segment = "Новый";
    if (diffDays > 45) {
      segment = "Спящий (45+)";
    } else if (data[i][8] > 3) { // Больше 3 визитов
      segment = "Постоянный";
    }

    sheet.getRange(i + 1, 10).setValue(segment); // Записываем в 10-й столбец J
  }

  SpreadsheetApp.getUi().alert('Сегментация успешно обновлена!');
}
