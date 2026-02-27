(function () {
  if (!window.requireAuth || !window.requireAuth()) return;

  var API_BASE = window.API_BASE_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');
  var fetchApi = window.fetchWithAuth || fetch;

  var todayEl = document.getElementById('todayContent');
  var monthEl = document.getElementById('monthContent');
  var empAnalyticsEl = document.getElementById('empAnalyticsContent');

  function showErr(el, msg) {
    if (!el) return;
    el.innerHTML = '<span class="error">' + (msg || 'Ошибка загрузки') + '</span>';
  }

  function getDateParams(prefix) {
    var fromEl = document.getElementById(prefix + 'DateFrom');
    var toEl = document.getElementById(prefix + 'DateTo');
    var fromVal = fromEl && fromEl.value ? fromEl.value : '';
    var toVal = toEl && toEl.value ? toEl.value : '';
    var q = [];
    if (fromVal) q.push('date_from=' + encodeURIComponent(fromVal));
    if (toVal) q.push('date_to=' + encodeURIComponent(toVal));
    return q.length ? '?' + q.join('&') : '';
  }

  function getEmpDateParams() {
    var fromEl = document.getElementById('empDateFrom');
    var toEl = document.getElementById('empDateTo');
    var fromVal = fromEl && fromEl.value ? fromEl.value : '';
    var toVal = toEl && toEl.value ? toEl.value : '';
    var q = ['period=' + getEmpPeriod()];
    if (fromVal) q.push('date_from=' + encodeURIComponent(fromVal));
    if (toVal) q.push('date_to=' + encodeURIComponent(toVal));
    return '?' + q.join('&');
  }

  async function loadToday() {
    if (!todayEl) return;
    try {
      var today = new Date();
      var from = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0') + '-' + String(today.getDate()).padStart(2, '0');
      var r = await fetchApi(API_BASE + '/analytics/today?date_from=' + encodeURIComponent(from) + '&date_to=' + encodeURIComponent(from));
      if (!r.ok) throw new Error(r.statusText);
      var d = await r.json();
      todayEl.innerHTML = [
        '<div class="stats">',
        '<div class="stat"><strong>' + Number(d.total_revenue) + ' ₽</strong><span>Выручка за день</span></div>',
        '<div class="stat"><strong>' + (d.orders_count || 0) + '</strong><span>Оплаченных заказов</span></div>',
        '<div class="stat"><strong>' + Number(d.state_duty_total) + ' ₽</strong><span>Госпошлина</span></div>',
        '<div class="stat"><strong>' + Number(d.income_pavilion1) + ' ₽</strong><span>Доход павильон 1</span></div>',
        '<div class="stat"><strong>' + Number(d.income_pavilion2) + ' ₽</strong><span>Доход павильон 2</span></div>',
        '</div>',
      ].join('');
    } catch (e) {
      showErr(todayEl, e.message);
    }
  }

  async function loadMonth() {
    if (!monthEl) return;
    try {
      var r = await fetchApi(API_BASE + '/analytics/month' + getDateParams('month'));
      if (!r.ok) throw new Error(r.statusText);
      var d = await r.json();
      monthEl.innerHTML = [
        '<div class="stats">',
        '<div class="stat"><strong>' + Number(d.total_revenue) + ' ₽</strong><span>Выручка за месяц</span></div>',
        '<div class="stat"><strong>' + (d.orders_count || 0) + '</strong><span>Оплаченных заказов</span></div>',
        '<div class="stat"><strong>' + Number(d.state_duty_total) + ' ₽</strong><span>Госпошлина</span></div>',
        '<div class="stat"><strong>' + Number(d.income_pavilion1) + ' ₽</strong><span>Доход павильон 1</span></div>',
        '<div class="stat"><strong>' + Number(d.income_pavilion2) + ' ₽</strong><span>Доход павильон 2</span></div>',
        '</div>',
      ].join('');
    } catch (e) {
      showErr(monthEl, e.message);
    }
  }

  function getEmpPeriod() {
    var sel = document.getElementById('empPeriodFilter');
    return sel && sel.value ? sel.value : 'day';
  }

  async function loadEmpAnalytics() {
    if (!empAnalyticsEl) return;
    try {
      var r = await fetchApi(API_BASE + '/analytics/employees' + getEmpDateParams());
      if (!r.ok) throw new Error(r.statusText);
      var d = await r.json();
      if (!d.employees || !d.employees.length) {
        empAnalyticsEl.innerHTML = '<p class="text-muted">Нет данных за выбранный период.</p>';
        return;
      }
      var rows = d.employees.map(function (e) {
        return '<tr><td>' + (e.employee_name || '—') + '</td><td>' + (e.orders_count || 0) + '</td><td>' + Number(e.total_amount) + ' ₽</td></tr>';
      });
      empAnalyticsEl.innerHTML =
        '<table><thead><tr><th>Сотрудник</th><th>Заказов</th><th>Сумма</th></tr></thead><tbody>' +
        rows.join('') +
        '</tbody></table>';
    } catch (e) {
      showErr(empAnalyticsEl, e.message);
    }
  }

  function bindFilters() {
    var empSel = document.getElementById('empPeriodFilter');
    if (empSel) empSel.addEventListener('change', loadEmpAnalytics);
    ['monthDateFrom', 'monthDateTo'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener('change', loadMonth);
    });
    ['empDateFrom', 'empDateTo'].forEach(function (id) {
      var el = document.getElementById(id);
      if (el) el.addEventListener('change', loadEmpAnalytics);
    });
  }

  function bindExport() {
    var btn = document.getElementById('btnExportCsv');
    if (!btn) return;
    btn.addEventListener('click', function () {
      var period = document.getElementById('exportPeriod').value;
      var fromEl = document.getElementById('exportDateFrom');
      var toEl = document.getElementById('exportDateTo');
      var fromVal = fromEl && fromEl.value ? fromEl.value : '';
      var toVal = toEl && toEl.value ? toEl.value : '';
      var q = ['format=csv', 'period=' + period];
      if (fromVal) q.push('date_from=' + encodeURIComponent(fromVal));
      if (toVal) q.push('date_to=' + encodeURIComponent(toVal));
      var url = API_BASE + '/analytics/export?' + q.join('&');
      fetchApi(url)
        .then(function (r) {
          if (!r.ok) throw new Error(r.statusText);
          return r.text();
        })
        .then(function (text) {
          var blob = new Blob([text], { type: 'text/csv;charset=utf-8' });
          var a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = 'analytics_' + period + '.csv';
          a.click();
          URL.revokeObjectURL(a.href);
        })
        .catch(function (e) {
          alert('Ошибка экспорта: ' + (e.message || ''));
        });
    });
  }

  function refresh() {
    if (todayEl) todayEl.textContent = 'Загрузка…';
    if (monthEl) monthEl.textContent = 'Загрузка…';
    if (empAnalyticsEl) empAnalyticsEl.textContent = 'Загрузка…';
    loadToday();
    loadMonth();
    loadEmpAnalytics();
  }

  function init() {
    bindFilters();
    bindExport();
    var btn = document.getElementById('btnRefresh');
    if (btn) btn.addEventListener('click', refresh);
    refresh();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

