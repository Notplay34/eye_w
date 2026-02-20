/**
 * Касса (павильон 1) — логика таблицы, сохранение, итоги. CRM-стиль.
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

  function formatNumSpaces(n) {
    var s = formatNum(n);
    return s.replace(/\u00a0/g, ' ') + ' ₽';
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

  function makeInput(row, key, isNum) {
    var val = row[key];
    var input = document.createElement('input');
    input.type = isNum ? 'number' : 'text';
    input.className = 'cash-crm__input' + (isNum ? ' cash-crm__input--num' : '');
    input.step = '0.01';
    input.min = '0';
    input.value = isNum ? (val != null && val !== '' ? Number(val) : '') : (val || '');
    input.dataset.key = key;
    input.dataset.rowId = String(row.id);
    if (isNum) input.setAttribute('inputmode', 'decimal');

    input.addEventListener('blur', function () {
      var tr = this.closest('tr');
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
      if (['application', 'state_duty', 'dkp', 'insurance', 'plates'].indexOf(k) >= 0 && tr) {
        var sum = 0;
        ['application', 'state_duty', 'dkp', 'insurance', 'plates'].forEach(function (key) {
          var inp = tr.querySelector('input[data-key="' + key + '"]');
          if (inp) sum += numVal(inp.value);
        });
        payload.total = sum;
      }
      patchRow(id, payload)
        .then(function (updated) {
          updateRowInList(id, updated);
          var totalSpan = tr && tr.querySelector('.cash-crm__row-total');
          if (totalSpan && payload.total !== undefined) {
            totalSpan.textContent = formatNumSpaces(payload.total);
            totalSpan.classList.toggle('cash-crm__row-total--negative', payload.total < 0);
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
    var tr = document.createElement('tr');
    if (isNew) tr.classList.add('cash-crm__row-new');
    tr.dataset.rowId = String(row.id);

    var tdName = document.createElement('td');
    tdName.className = 'cash-crm__td-name';
    tdName.appendChild(makeInput(row, 'client_name', false));
    tr.appendChild(tdName);

    ['application', 'state_duty', 'dkp', 'insurance', 'plates'].forEach(function (key) {
      var td = document.createElement('td');
      td.className = 'cash-crm__td-num';
      td.appendChild(makeInput(row, key, true));
      tr.appendChild(td);
    });

    var total = recalcTotal(row);
    var tdTotal = document.createElement('td');
    tdTotal.className = 'cash-crm__td-num';
    var totalSpan = document.createElement('span');
    totalSpan.className = 'cash-crm__row-total' + (total < 0 ? ' cash-crm__row-total--negative' : '');
    totalSpan.textContent = formatNumSpaces(total);
    tdTotal.appendChild(totalSpan);
    tr.appendChild(tdTotal);

    var tdDel = document.createElement('td');
    tdDel.className = 'cash-crm__td-del';
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
    tdDel.appendChild(btnDel);
    tr.appendChild(tdDel);
    return tr;
  }

  function renderTotal() {
    var total = rows.reduce(function (sum, r) { return sum + numVal(r.total); }, 0);
    if (!totalEl) return;
    totalEl.textContent = formatNumSpaces(total);
    totalEl.classList.toggle('cash-crm__total-value--negative', total < 0);
  }

  function render() {
    var tbody = document.getElementById('cashBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (rows.length === 0) {
      var tr = document.createElement('tr');
      tr.className = 'cash-crm__row-placeholder';
      tr.innerHTML = '<td colspan="8" class="cash-crm__placeholder">Нет строк. Нажмите «Добавить строку», чтобы начать.</td>';
      tbody.appendChild(tr);
      renderTotal();
      return;
    }

    var lastDay = null;
    rows.forEach(function (row) {
      var d = dayKey(row);
      if (d && d !== lastDay) {
        lastDay = d;
        var sep = document.createElement('tr');
        sep.className = 'cash-crm__row-day';
        sep.innerHTML = '<td colspan="8">' + dayLabel(d) + '</td>';
        tbody.appendChild(sep);
      }
      tbody.appendChild(renderRow(row, false));
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
        var tbody = document.getElementById('cashBody');
        if (tbody) {
          tbody.innerHTML = '<tr class="cash-crm__row-placeholder"><td colspan="8" class="cash-crm__placeholder">Ошибка загрузки: ' + (e.message || '') + '</td></tr>';
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
        var tbody = document.getElementById('cashBody');
        tbody.innerHTML = '';
        var lastDay = null;
        rows.forEach(function (row) {
          var d = dayKey(row);
          if (d && d !== lastDay) {
            lastDay = d;
            var sep = document.createElement('tr');
            sep.className = 'cash-crm__row-day';
            sep.innerHTML = '<td colspan="8">' + dayLabel(d) + '</td>';
            tbody.appendChild(sep);
          }
          tbody.appendChild(renderRow(row, row.id === newRow.id));
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
