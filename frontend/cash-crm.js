/**
 * Касса — премиальный финтех UI. Grid-верстка, табличные цифры, без переносов.
 */
(function () {
  var API = window.API_BASE_URL || '';
  var fetchApi = window.fetchWithAuth || fetch;
  if (!window.getToken || !window.getToken()) return;

  var user = window.getUser();
  if (user) document.getElementById('userName').textContent = user.name || '';

  var rows = [];
  var msgEl = document.getElementById('cashMsg');
  var totalEl = document.getElementById('cashTotalCell');
  var bodyEl = document.getElementById('cashBody');

  function msg(t, type) {
    if (!msgEl) return;
    msgEl.textContent = t || '';
    msgEl.className = 'cash-crm__msg' + (type === 'err' ? ' err' : type === 'ok' ? ' ok' : '');
    if (t && type !== 'err') setTimeout(function () { msg(''); }, 2000);
  }

  function numVal(v) {
    var s = String(v).replace(/\s/g, '').replace(',', '.');
    var n = parseFloat(s);
    return isNaN(n) ? 0 : n;
  }

  function formatNum(n) {
    return new Intl.NumberFormat('ru-RU', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(n);
  }

  /** Только число с пробелами, без " ₽" — для вставки в разметку */
  function formatNumOnly(n) {
    return new Intl.NumberFormat('ru-RU', {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(n).replace(/\u00a0/g, ' ');
  }

  function patchRow(rowId, payload) {
    return fetchApi(API + '/cash/rows/' + rowId, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    }).then(function (r) {
      if (!r.ok) return r.json().then(function (j) { throw new Error(j.detail || r.statusText); });
      return r.json();
    });
  }

  function updateRowInList(id, data) {
    for (var i = 0; i < rows.length; i++) {
      if (rows[i].id === id) {
        rows[i] = data;
        return;
      }
    }
  }

  function recalcTotal(row) {
    return (
      numVal(row.application) +
      numVal(row.state_duty) +
      numVal(row.dkp) +
      numVal(row.insurance) +
      numVal(row.plates)
    );
  }

  function rowTotalClass(total) {
    if (total === 0) return 'cash-crm__row-total--zero';
    if (total < 0) return 'cash-crm__row-total--negative';
    return 'cash-crm__row-total--positive';
  }

  function makeInput(row, key, isNum) {
    var val = row[key];
    var input = document.createElement('input');
    input.type = isNum ? 'number' : 'text';
    input.className = 'cash-crm__input' + (isNum ? ' cash-crm__input--num' : '');
    input.step = '0.01';
    /* без min — разрешаем отрицательные (возвраты, корректировки) */
    input.value = isNum ? (val != null && val !== '' ? Number(val) : '') : (val || '');
    input.dataset.key = key;
    input.dataset.rowId = String(row.id);
    if (isNum) input.setAttribute('inputmode', 'decimal');

    input.addEventListener('blur', function () {
      var rowEl = this.closest('.cash-crm__grid-row');
      var id = parseInt(this.dataset.rowId, 10);
      var k = this.dataset.key;
      var raw = this.value;
      var v = isNum ? numVal(raw) : raw.trim();
      if (isNum && key !== 'client_name') {
        this.value = v === 0 ? '' : formatNum(v);
      }
      var prev = rows.find(function (r) { return r.id === id; });
      if (!prev) return;
      var prevVal = prev[k];
      if (isNum && prevVal === v && k !== 'client_name') return;
      if (!isNum && String(prevVal || '') === String(v)) return;
      var payload = {};
      payload[k] = isNum ? v : v;
      if (['application', 'state_duty', 'dkp', 'insurance', 'plates'].indexOf(k) >= 0 && rowEl) {
        var sum = 0;
        ['application', 'state_duty', 'dkp', 'insurance', 'plates'].forEach(function (key) {
          var inp = rowEl.querySelector('input[data-key="' + key + '"]');
          if (inp) sum += numVal(inp.value);
        });
        payload.total = sum;
      }
      patchRow(id, payload)
        .then(function (updated) {
          updateRowInList(id, updated);
          var totalWrap = rowEl && rowEl.querySelector('.cash-crm__row-total');
          if (totalWrap) {
            var total = numVal(updated.total);
            var numSpan = totalWrap.querySelector('.cash-crm__amount-num');
            if (numSpan) numSpan.textContent = formatNumOnly(total);
            totalWrap.className = 'cash-crm__row-total ' + rowTotalClass(total);
          }
          renderTotal();
          msg('Сохранено', 'ok');
        })
        .catch(function (e) {
          msg('Ошибка: ' + (e.message || 'не удалось сохранить'), 'err');
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
    var y = d.getFullYear(),
      m = d.getMonth() + 1,
      day = d.getDate();
    return y + '-' + (m < 10 ? '0' : '') + m + '-' + (day < 10 ? '0' : '') + day;
  }

  function dayLabel(key) {
    if (!key) return '';
    var parts = key.split('-');
    if (parts.length !== 3) return key;
    return parts[2] + '.' + parts[1] + '.' + parts[0];
  }

  function renderRow(row, isNew) {
    var total = recalcTotal(row);
    var rowEl = document.createElement('div');
    rowEl.className = 'cash-crm__grid-row' + (isNew ? ' cash-crm__grid-row--new' : '');
    rowEl.dataset.rowId = String(row.id);

    var cellName = document.createElement('div');
    cellName.className = 'cash-crm__grid-cell cash-crm__grid-cell--name';
    cellName.appendChild(makeInput(row, 'client_name', false));
    rowEl.appendChild(cellName);

    ['application', 'state_duty', 'dkp', 'insurance', 'plates'].forEach(function (key) {
      var cell = document.createElement('div');
      cell.className = 'cash-crm__grid-cell cash-crm__grid-cell--num';
      cell.appendChild(makeInput(row, key, true));
      rowEl.appendChild(cell);
    });

    var cellTotal = document.createElement('div');
    cellTotal.className = 'cash-crm__grid-cell cash-crm__grid-cell--num';
    var totalWrap = document.createElement('span');
    totalWrap.className = 'cash-crm__row-total ' + rowTotalClass(total);
    totalWrap.innerHTML = '<span class="cash-crm__amount-num">' + formatNumOnly(total) + '</span><span class="cash-crm__amount-currency"> ₽</span>';
    cellTotal.appendChild(totalWrap);
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
            rows = rows.filter(function (r) { return r.id !== row.id; });
            render();
          } else return r.json().then(function (j) { throw new Error(j.detail || r.statusText); });
        })
        .catch(function (e) {
          msg('Ошибка: ' + (e.message || 'не удалось удалить'), 'err');
        });
    };
    cellDel.appendChild(btnDel);
    rowEl.appendChild(cellDel);

    return rowEl;
  }

  function renderTotal() {
    var total = rows.reduce(function (sum, r) { return sum + numVal(r.total); }, 0);
    if (!totalEl) return;
    var numSpan = totalEl.querySelector('.cash-crm__amount-num');
    if (numSpan) numSpan.textContent = formatNumOnly(total);
    totalEl.classList.remove('cash-crm__total-value--negative', 'cash-crm__total-value--positive');
    if (total < 0) totalEl.classList.add('cash-crm__total-value--negative');
    else if (total > 0) totalEl.classList.add('cash-crm__total-value--positive');
  }

  function render() {
    if (!bodyEl) return;
    bodyEl.innerHTML = '';

    if (rows.length === 0) {
      var placeholderRow = document.createElement('div');
      placeholderRow.className = 'cash-crm__grid-row cash-crm__grid-row--placeholder';
      placeholderRow.innerHTML = '<div class="cash-crm__grid-cell cash-crm__placeholder">Нет строк. Нажмите «Добавить строку», чтобы начать.</div>';
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

  function load() {
    fetchApi(API + '/cash/rows')
      .then(function (r) {
        if (!r.ok) return r.json().then(function (j) { throw new Error(j.detail || r.statusText); });
        return r.json();
      })
      .then(function (data) {
        rows = data || [];
        render();
      })
      .catch(function (e) {
        if (bodyEl) {
          bodyEl.innerHTML = '<div class="cash-crm__grid-row cash-crm__grid-row--placeholder"><div class="cash-crm__grid-cell cash-crm__placeholder">Ошибка загрузки: ' + (e.message || '') + '</div></div>';
        }
        msg('Ошибка загрузки', 'err');
      });
  }

  document.getElementById('btnAddRow').onclick = function () {
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
        if (!r.ok) return r.json().then(function (j) { throw new Error(j.detail || r.statusText); });
        return r.json();
      })
      .then(function (newRow) {
        rows.unshift(newRow);
        bodyEl.innerHTML = '';
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
          bodyEl.appendChild(renderRow(row, row.id === newRow.id));
        });
        renderTotal();
        msg('Строка добавлена', 'ok');
      })
      .catch(function (e) {
        msg('Ошибка: ' + (e.message || 'не удалось добавить'), 'err');
      });
  };

  load();
})();
