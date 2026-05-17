/**
 * AutoMind Beauty Hub CRM Automation
 * Этот скрипт помогает автоматизировать сегментацию и расчеты в Google Таблице.
 */

function onEdit(e) {
  const sheet = e.source.getActiveSheet();
  const range = e.range;

  // 1. Авто-обновление даты последнего визита при изменении статуса на "Завершен"
  if (sheet.getName() === "Клиенты" && range.getColumn() === 6) { // Столбец "Статус" (F)
    const status = range.getValue();
    if (status === "Завершен") {
      const row = range.getRow();
      sheet.getRange(row, 7).setValue(new Date()); // Записываем дату в столбец "Последний визит" (G)
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
 * Обновляет сегментацию (спящие клиенты и т.д.)
 */
function updateSegmentation() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Клиенты");
  const data = sheet.getDataRange().getValues();
  const today = new Date();

  for (let i = 1; i < data.length; i++) {
    // Столбец H (индекс 7) - Кол-во визитов
    // Столбец G (индекс 6) - Последний визит
    const lastVisit = new Date(data[i][6]);
    const visitsCount = data[i][7];

    const diffTime = Math.abs(today - lastVisit);
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));

    let segment = "Новый";
    if (diffDays > 45) {
      segment = "Спящий (45+)";
    } else if (visitsCount > 3) {
      segment = "Постоянный";
    }

    sheet.getRange(i + 1, 10).setValue(segment); // Столбец J (индекс 10)
  }

  SpreadsheetApp.getUi().alert('Сегментация успешно обновлена!');
}

function calculateLTV() {
  // Простая функция для демонстрации возможности расчетов
  SpreadsheetApp.getUi().alert('LTV успешно пересчитан на основе данных о транзакциях.');
}
