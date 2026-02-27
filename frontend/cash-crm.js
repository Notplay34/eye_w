/**
 * Касса павильона 1 — простая и предсказуемая:
 * - одна строка = один клиент/операция;
 * - пять колонок сумм (могут быть отрицательными для возвратов/корректировок);
 * - итог по строке считается автоматически, но при необходимости можно ввести руками;
 * - общий итог по кассе = сумма всех строк.
 *
 * Требования:
 * - поддержка отрицательных значений (возвраты);
 * - ввод через запятую и с пробелами;
 * - никакого «исчезновения» сумм при повторном клике;
 * - цвета: ноль / плюс / минус;
 * - работа только через API `/cash/rows`.
 */
(function () {
  var API = window.API_BASE_URL || '';
  var fetchApi = window.fetchWithAuth || fetch;
  if (!window.getToken || !window.getToken()) return;

  var user = window.getUser();
  var userNameEl = document.getElementById('userName');
  if (user && userNameEl) userNameEl.textContent = user.name || '';

  var rows = [];
  var msgEl = document.getElementById('cashMsg');
  var totalEl = document.getElementById('cashTotalCell');
  var bodyEl = document.getElementById('cashBody');

  /** Сообщение внизу таблицы */
  function showMsg(text, type) {
    if (!msgEl) return;
    msgEl.textContent = text || '';
    msgEl.className = 'cash-crm__msg' + (type === 'err' ? ' err' : type === 'ok' ? ' ok' : '');
    if (text && type !== 'err') {
      setTimeout(function () {
        if (msgEl.textContent === text) showMsg('');
      }, 2000);
    }
  }

  /** Нормализация числового ввода: поддержка пробелов, запятой и минуса */
  function parseAmount(raw) {
    if (raw === null || raw === undefined) return 0;
    var s = String(raw).trim();
    if (!s) return 0;
    s = s.replace(/\s/g, '').replace(',', '.');
    var n = parseFloat(s);
    return isNaN(n) ? 0 : n;
  }

  /** Число для поля total в модели (учитывает минус) */
  function rowTotalNum(row) {
    if (!row) return 0;
    var t = row.total;
    if (t === null || t === undefined) return 0;
    var n = Number(t);
    return isNaN(n) ? 0 : n;
  }

  /** Для отображения общей суммы (справа в карточке) */
  function formatNumOnly(n) {
    var num = Number(n);
    if (isNaN(num)) num = 0;
    return new Intl.NumberFormat('ru-RU', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(num).replace(/\u00a0/g, ' ');
  }

  /** Значение для input[type=number]: всегда валидный формат, без локализации */
  function formatForInput(v) {
    var n = Number(v);
    if (!isFinite(n)) return '';
    return n.toFixed(2);
  }

  function rowTotalClass(total) {
    if (total === 0) return 'cash-crm__row-total--zero';
    if (total < 0) return 'cash-crm__row-total--negative';
    return 'cash-crm__row-total--positive';
  }

  function patchRow(id, payload) {
    return fetchApi(API + '/cash/rows/' + id, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(function (r) {
      if (!r.ok) {
        return r.json().then(function (j) {
          throw new Error(j.detail || r.statusText);
        });
      }
      return r.json();
    });
  }

  function replaceRowInMemory(id, updated) {
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].id === id) {
        rows[i] = updated;
        return;
      }
    }
  }

  /** Пересчёт total из пяти колонок */
  function recomputeRowTotalFromFields(row) {
    if (!row) return 0;
    var sum =
      parseAmount(row.application) +
      parseAmount(row.state_duty) +
      parseAmount(row.dkp) +
      parseAmount(row.insurance) +
      parseAmount(row.plates);
    row.total = sum;
    return sum;
  }

  /** Вводимое поле total по строке (редактируемое, допускает минус).
   * Используем type="text", чтобы браузер не очищал значение из-за локали.
   */
  function buildTotalCell(row) {
    var id = row.id;
    var total = rowTotalNum(row);
    var wrap = document.createElement('span');
    wrap.className = 'cash-crm__row-total ' + rowTotalClass(total);

    var input = document.createElement('input');
    input.type = 'text';
    input.className = 'cash-crm__input cash-crm__input--num cash-crm__input--total';
    input.dataset.rowId = String(id);
    input.setAttribute('inputmode', 'decimal');
    input.value = total === 0 ? '' : formatForInput(total);

    input.addEventListener('input', function () {
      var v = parseAmount(this.value);
      var r = rows.find(function (x) { return x.id === id; });
      if (r) r.total = v;
      wrap.className = 'cash-crm__row-total ' + rowTotalClass(v);
      renderTotal();
    });

    input.addEventListener('blur', function () {
      var v = parseAmount(this.value);
      var r = rows.find(function (x) { return x.id === id; });
      if (!r) return;

      // Пустое поле оставляем пустым, ноль — "0.00", остальное — число
      if (this.value.trim() === '') {
        this.value = '';
      } else {
        this.value = formatForInput(v);
      }

      if (rowTotalNum(r) === v) {
        wrap.className = 'cash-crm__row-total ' + rowTotalClass(v);
        renderTotal();
        return;
      }

      patchRow(id, { total: v })
        .then(function (updated) {
          replaceRowInMemory(id, updated);
          var t = rowTotalNum(updated);
          input.value = t === 0 ? '' : formatForInput(t);
          wrap.className = 'cash-crm__row-total ' + rowTotalClass(t);
          renderTotal();
          showMsg('Сохранено', 'ok');
        })
        .catch(function (e) {
          showMsg('Ошибка: ' + (e.message || 'не удалось сохранить'), 'err');
        });
    });

    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') this.blur();
    });

    wrap.appendChild(input);
    var currency = document.createElement('span');
    currency.className = 'cash-crm__amount-currency';
    currency.textContent = ' ₽';
    wrap.appendChild(currency);
    return wrap;
  }

  /** Универсальное поле ввода (ФИО или сумма).
   * Для сумм используем type="text", чтобы не было автоочистки браузером.
   */
  function buildCellInput(row, key, isNumber) {
    var input = document.createElement('input');
    input.type = 'text';
    input.className = 'cash-crm__input' + (isNumber ? ' cash-crm__input--num' : '');
    if (isNumber) {
      input.setAttribute('inputmode', 'decimal');
      var n = parseAmount(row[key]);
      input.value = n === 0 ? '' : formatForInput(n);
    } else {
      input.value = row[key] || '';
    }
    input.dataset.key = key;
    input.dataset.rowId = String(row.id);

    // Мгновенный пересчёт total при правке сумм
    if (isNumber && ['application', 'state_duty', 'dkp', 'insurance', 'plates'].indexOf(key) !== -1) {
      input.addEventListener('input', function () {
        var rowEl = this.closest('.cash-crm__grid-row');
        refreshRowTotalFromDom(rowEl);
      });
    }

    input.addEventListener('blur', function () {
      var id = parseInt(this.dataset.rowId, 10);
      if (isNaN(id)) return;
      var field = this.dataset.key;
      var currentRow = rows.find(function (r) { return r.id === id; });
      if (!currentRow) return;

      var raw = this.value;
      var newValue = isNumber ? parseAmount(raw) : raw.trim();

      if (isNumber) {
        if (raw.trim() === '') {
          this.value = '';
        } else {
          this.value = formatForInput(newValue);
        }
      }

      var prevVal = currentRow[field];
      if (!isNumber && String(prevVal || '') === String(newValue || '')) {
        return;
      }
      if (isNumber && Number(prevVal) === newValue) {
        return;
      }

      var payload = {};
      if (isNumber) {
        currentRow[field] = newValue;
        // при изменении любой суммы пересчитываем total на фронте и отправляем вместе
        var sum = recomputeRowTotalFromFields(currentRow);
        payload[field] = newValue;
        payload.total = sum;
      } else {
        payload[field] = newValue;
      }

      patchRow(id, payload)
        .then(function (updated) {
          replaceRowInMemory(id, updated);
          // синхронизируем total в DOM
          var rowEl = bodyEl && bodyEl.querySelector('.cash-crm__grid-row[data-row-id="' + id + '"]');
          if (rowEl) {
            var totalWrap = rowEl.querySelector('.cash-crm__row-total');
            var totalInput = totalWrap && totalWrap.querySelector('input.cash-crm__input--total');
            var total = rowTotalNum(updated);
            if (totalWrap) totalWrap.className = 'cash-crm__row-total ' + rowTotalClass(total);
            if (totalInput) totalInput.value = total === 0 ? '' : formatForInput(total);
          }
          renderTotal();
          showMsg('Сохранено', 'ok');
        })
        .catch(function (e) {
          showMsg('Ошибка: ' + (e.message || 'не удалось сохранить'), 'err');
        });
    });

    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') this.blur();
    });

    return input;
  }

  function dayKey(row) {
    var s = row.created_at;
    if (!s) return '';
    var d = new Date(s);
    if (isNaN(d.getTime())) return '';
    var y = d.getFullYear();
    var m = d.getMonth() + 1;
    var day = d.getDate();
    return y + '-' + (m < 10 ? '0' : '') + m + '-' + (day < 10 ? '0' : '') + day;
  }

  function dayLabel(key) {
    if (!key) return '';
    var parts = key.split('-');
    if (parts.length !== 3) return key;
    return parts[2] + '.' + parts[1] + '.' + parts[0];
  }

  function renderRow(row, isNew) {
    var rowEl = document.createElement('div');
    rowEl.className = 'cash-crm__grid-row' + (isNew ? ' cash-crm__grid-row--new' : '');
    rowEl.dataset.rowId = String(row.id);

    var cellName = document.createElement('div');
    cellName.className = 'cash-crm__grid-cell cash-crm__grid-cell--name';
    cellName.appendChild(buildCellInput(row, 'client_name', false));
    rowEl.appendChild(cellName);

    ['application', 'state_duty', 'dkp', 'insurance', 'plates'].forEach(function (key) {
      var cell = document.createElement('div');
      cell.className = 'cash-crm__grid-cell cash-crm__grid-cell--num';
      cell.appendChild(buildCellInput(row, key, true));
      rowEl.appendChild(cell);
    });

    var cellTotal = document.createElement('div');
    cellTotal.className = 'cash-crm__grid-cell cash-crm__grid-cell--num';
    cellTotal.appendChild(buildTotalCell(row));
    rowEl.appendChild(cellTotal);

    var cellDel = document.createElement('div');
    cellDel.className = 'cash-crm__grid-cell cash-crm__grid-cell--del';
    var btnDel = document.createElement('button');
    btnDel.type = 'button';
    btnDel.className = 'cash-crm__btn-del';
    btnDel.title = 'Удалить строку';
    btnDel.innerHTML = '🗑';
    btnDel.setAttribute('aria-label', 'Удалить строку');
    btnDel.onclick = function () {
      if (!confirm('Удалить эту строку из кассы?')) return;
      fetchApi(API + '/cash/rows/' + row.id, { method: 'DELETE' })
        .then(function (r) {
          if (r.status === 204 || r.ok) {
            rows = rows.filter(function (x) { return x.id !== row.id; });
            render();
            showMsg('Строка удалена', 'ok');
          } else {
            return r.json().then(function (j) { throw new Error(j.detail || r.statusText); });
          }
        })
        .catch(function (e) {
          showMsg('Ошибка: ' + (e.message || 'не удалось удалить'), 'err');
        });
    };
    cellDel.appendChild(btnDel);
    rowEl.appendChild(cellDel);

    return rowEl;
  }

  /** Пересчёт общей суммы в кассе */
  function renderTotal() {
    var total = rows.reduce(function (sum, r) {
      return sum + rowTotalNum(r);
    }, 0);
    total = Number(total);
    if (!isFinite(total)) total = 0;
    if (!totalEl) return;

    var numSpan = totalEl.querySelector('.cash-crm__amount-num');
    if (numSpan) numSpan.textContent = formatNumOnly(total);

    totalEl.classList.remove('cash-crm__total-value--negative', 'cash-crm__total-value--positive');
    if (total < 0) totalEl.classList.add('cash-crm__total-value--negative');
    else if (total > 0) totalEl.classList.add('cash-crm__total-value--positive');
  }

  /** Пересчёт total по строке на основе текущих значений пяти полей из DOM */
  function refreshRowTotalFromDom(rowEl) {
    if (!rowEl) return;
    var id = parseInt(rowEl.dataset.rowId, 10);
    if (isNaN(id)) return;

    var sum = 0;
    ['application', 'state_duty', 'dkp', 'insurance', 'plates'].forEach(function (key) {
      var inp = rowEl.querySelector('input[data-key="' + key + '"]');
      if (inp) sum += parseAmount(inp.value);
    });

    var row = rows.find(function (r) { return r.id === id; });
    if (row) row.total = sum;

    var totalWrap = rowEl.querySelector('.cash-crm__row-total');
    var totalInput = totalWrap && totalWrap.querySelector('input.cash-crm__input--total');
    if (totalWrap) totalWrap.className = 'cash-crm__row-total ' + rowTotalClass(sum);
    if (totalInput) totalInput.value = sum === 0 ? '' : formatForInput(sum);

    renderTotal();
  }

  function render() {
    if (!bodyEl) return;
    bodyEl.innerHTML = '';

    if (!rows.length) {
      var placeholderRow = document.createElement('div');
      placeholderRow.className = 'cash-crm__grid-row cash-crm__grid-row--placeholder';
      placeholderRow.innerHTML =
        '<div class="cash-crm__grid-cell cash-crm__placeholder" style="grid-column: 1 / -1;">Нет строк. Нажмите «Добавить строку», чтобы начать.</div>';
      bodyEl.appendChild(placeholderRow);
      renderTotal();
      return;
    }

    var lastDay = null;
    rows.forEach(function (row) {
      var d = dayKey(row);
      if (d && d !== lastDay) {
        lastDay = d;
        var sepRow = document.createElement('div');
        sepRow.className = 'cash-crm__grid-row-day';
        sepRow.innerHTML = '<div class="cash-crm__grid-cell">' + dayLabel(d) + '</div>';
        bodyEl.appendChild(sepRow);
      }
      bodyEl.appendChild(renderRow(row, false));
    });

    renderTotal();
  }

  function loadRows() {
    fetchApi(API + '/cash/rows')
      .then(function (r) {
        if (!r.ok) {
          return r.json().then(function (j) {
            throw new Error(j.detail || r.statusText);
          });
        }
        return r.json();
      })
      .then(function (data) {
        rows = Array.isArray(data) ? data : [];
        render();
      })
      .catch(function (e) {
        if (bodyEl) {
          bodyEl.innerHTML =
            '<div class="cash-crm__grid-row cash-crm__grid-row--placeholder"><div class="cash-crm__grid-cell cash-crm__placeholder">Ошибка загрузки: ' +
            (e.message || '') +
            '</div></div>';
        }
        showMsg('Ошибка загрузки', 'err');
      });
  }

  function addRow() {
    fetchApi(API + '/cash/rows', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        client_name: '',
        application: 0,
        state_duty: 0,
        dkp: 0,
        insurance: 0,
        plates: 0,
        total: 0,
      }),
    })
      .then(function (r) {
        if (!r.ok) {
          return r.json().then(function (j) {
            throw new Error(j.detail || r.statusText);
          });
        }
        return r.json();
      })
      .then(function (newRow) {
        rows.unshift(newRow);
        render();
        showMsg('Строка добавлена', 'ok');
      })
      .catch(function (e) {
        showMsg('Ошибка: ' + (e.message || 'не удалось добавить'), 'err');
      });
  }

  function init() {
    // Берём актуальные DOM-элементы после того, как страница загрузилась
    bodyEl = document.getElementById('cashBody');
    totalEl = document.getElementById('cashTotalCell');
    msgEl = document.getElementById('cashMsg');
    if (!bodyEl) return;
    loadRows();
    var btn = document.getElementById('btnAddRow');
    if (btn) btn.onclick = addRow;
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
