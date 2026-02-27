(function () {
  if (!window.requireAuth || !window.requireAuth()) return;

  var API_BASE = window.API_BASE_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');
  var fetchApi = window.fetchWithAuth || fetch;

  var kpiEl = document.getElementById('kpiPlatesContent');
  var dynEl = document.getElementById('dynamicsPlatesContent');
  var empEl = document.getElementById('employeesPlatesContent');

  function setLoading(el, isLoading) {
    if (!el) return;
    if (isLoading) {
      el.classList.add('analytics-block--loading');
      el.innerHTML = '<div class="analytics-block__loader">Загрузка…</div>';
    } else {
      el.classList.remove('analytics-block--loading');
    }
  }

  function formatMoney(n) {
    var num = Number(n || 0);
    if (!isFinite(num)) num = 0;
    return new Intl.NumberFormat('ru-RU', {
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(num) + ' ₽';
  }

  function calcDelta(current, previous) {
    var c = Number(current || 0);
    var p = Number(previous || 0);
    if (!isFinite(c)) c = 0;
    if (!isFinite(p)) p = 0;
    if (p === 0) {
      if (c === 0) return { value: 0, cls: 'delta--zero' };
      return { value: 100, cls: 'delta--up' };
    }
    var diff = ((c - p) / Math.abs(p)) * 100;
    var cls = diff > 0 ? 'delta--up' : diff < 0 ? 'delta--down' : 'delta--zero';
    return { value: diff, cls: cls };
  }

  function renderDelta(current, previous) {
    var d = calcDelta(current, previous);
    var sign = d.value > 0 ? '+' : '';
    var valueStr = sign + d.value.toFixed(1) + ' %';
    return '<span class="delta ' + d.cls + '">' + valueStr + '</span>';
  }

  function getSummaryPeriod() {
    var sel = document.getElementById('summaryPeriodPlates');
    var v = sel && sel.value ? sel.value : 'day';
    if (v !== 'day' && v !== 'week' && v !== 'month') return 'day';
    return v;
  }

  async function loadSummaryPlates() {
    if (!kpiEl) return;
    setLoading(kpiEl, true);
    var period = getSummaryPeriod();
    try {
      var q = '?period=' + encodeURIComponent(period);
      var r = await fetchApi(API_BASE + '/analytics/summary' + q);
      if (!r.ok) throw new Error(r.statusText);
      var data = await r.json();
      var cur = data.current || {};
      var prev = data.previous || {};

      var cards = [];
      cards.push({
        key: 'total_revenue',
        label: 'Общая выручка',
        current: cur.total_revenue,
        previous: prev.total_revenue,
      });
      cards.push({
        key: 'net_income',
        label: 'Чистый доход',
        current: cur.net_income,
        previous: prev.net_income,
      });
      cards.push({
        key: 'state_duty_total',
        label: 'Госпошлина',
        current: cur.state_duty_total,
        previous: prev.state_duty_total,
      });
      cards.push({
        key: 'average_check',
        label: 'Средний чек',
        current: cur.average_check,
        previous: prev.average_check,
      });
      cards.push({
        key: 'orders_count',
        label: 'Заказов',
        current: cur.orders_count,
        previous: prev.orders_count,
      });
      cards.push({
        key: 'income_pavilion2',
        label: 'Доход — Номера (павильон 2)',
        current: cur.income_pavilion2,
        previous: prev.income_pavilion2,
        highlight: true,
      });
      cards.push({
        key: 'income_pavilion1',
        label: 'Доход — Документы (павильон 1)',
        current: cur.income_pavilion1,
        previous: prev.income_pavilion1,
      });

      var html = '<div class="kpi-grid">';
      cards.forEach(function (c) {
        var value =
          c.key === 'orders_count'
            ? (c.current || 0)
            : formatMoney(c.current);
        html +=
          '<article class="kpi-card' +
          (c.highlight ? ' kpi-card--highlight' : '') +
          '">' +
          '<div class="kpi-card__label">' +
          c.label +
          '</div>' +
          '<div class="kpi-card__value">' +
          value +
          '</div>' +
          '<div class="kpi-card__delta">' +
          renderDelta(c.current, c.previous) +
          '</div>' +
          '</article>';
      });
      html += '</div>';

      kpiEl.innerHTML = html;
      setLoading(kpiEl, false);
    } catch (e) {
      kpiEl.innerHTML = '<p class="error">Ошибка загрузки сводки.</p>';
    }
  }

  function getDynamicsGroup() {
    var sel = document.getElementById('dynamicsGroupPlates');
    var v = sel && sel.value ? sel.value : 'day';
    if (v !== 'day' && v !== 'week' && v !== 'month') return 'day';
    return v;
  }

  async function loadDynamicsPlates() {
    if (!dynEl) return;
    setLoading(dynEl, true);
    var groupBy = getDynamicsGroup();
    try {
      var r = await fetchApi(
        API_BASE + '/analytics/dynamics?group_by=' + encodeURIComponent(groupBy)
      );
      if (!r.ok) throw new Error(r.statusText);
      var data = await r.json();
      var points = data.points || [];
      if (!points.length) {
        dynEl.innerHTML = '<p class="text-caption">Нет данных для динамики.</p>';
        return;
      }
      var rows = points.map(function (p) {
        return (
          '<tr>' +
          '<td>' + p.period_start + '</td>' +
          '<td>' + formatMoney(p.total_revenue) + '</td>' +
          '<td>' + formatMoney(p.income_pavilion2) + '</td>' +
          '<td>' + formatMoney(p.net_income) + '</td>' +
          '</tr>'
        );
      });
      dynEl.innerHTML =
        '<div class="table-wrapper"><table class="table analytics-table">' +
        '<thead><tr><th>Период</th><th>Выручка, всего</th><th>Доход Номера</th><th>Чистый доход</th></tr></thead>' +
        '<tbody>' +
        rows.join('') +
        '</tbody></table></div>';
      setLoading(dynEl, false);
    } catch (e) {
      dynEl.innerHTML = '<p class="error">Ошибка загрузки динамики.</p>';
    }
  }

  function getEmpPeriodPlates() {
    var sel = document.getElementById('empPeriodPlates');
    var v = sel && sel.value ? sel.value : 'day';
    if (v !== 'day' && v !== 'week' && v !== 'month') return 'day';
    return v;
  }

  async function loadEmployeesPlates() {
    if (!empEl) return;
    setLoading(empEl, true);
    var period = getEmpPeriodPlates();
    try {
      var r = await fetchApi(
        API_BASE + '/analytics/employees?period=' + encodeURIComponent(period)
      );
      if (!r.ok) throw new Error(r.statusText);
      var data = await r.json();
      var list = data.employees || [];
      if (!list.length) {
        empEl.innerHTML = '<p class="text-caption">Нет данных по сотрудникам.</p>';
        return;
      }

      list.sort(function (a, b) {
        return Number(b.total_amount || 0) - Number(a.total_amount || 0);
      });

      function render(sortKey, asc) {
        var items = list.slice().sort(function (a, b) {
          var av = a[sortKey];
          var bv = b[sortKey];
          if (sortKey === 'employee_name') {
            av = (av || '').toString();
            bv = (bv || '').toString();
            if (av < bv) return asc ? -1 : 1;
            if (av > bv) return asc ? 1 : -1;
            return 0;
          }
          av = Number(av || 0);
          bv = Number(bv || 0);
          return asc ? av - bv : bv - av;
        });

        var rows = items.map(function (e) {
          return (
            '<tr>' +
            '<td>' + (e.employee_name || '—') + '</td>' +
            '<td>' + (e.orders_count || 0) + '</td>' +
            '<td>' + formatMoney(e.total_amount) + '</td>' +
            '<td>' + formatMoney(e.average_check) + '</td>' +
            '<td>' + (Number(e.share_percent || 0).toFixed(1)) + ' %</td>' +
            '</tr>'
          );
        });

        empEl.innerHTML =
          '<div class="table-wrapper"><table class="table analytics-table analytics-table--sortable">' +
          '<thead><tr>' +
          '<th data-sort="employee_name">Сотрудник</th>' +
          '<th data-sort="orders_count">Заказов</th>' +
          '<th data-sort="total_amount">Общая сумма</th>' +
          '<th data-sort="average_check">Средний чек</th>' +
          '<th data-sort="share_percent">Доля в выручке %</th>' +
          '</tr></thead>' +
          '<tbody>' +
          rows.join('') +
          '</tbody></table></div>';

        var ths = empEl.querySelectorAll('th[data-sort]');
        ths.forEach(function (th) {
          th.addEventListener('click', function () {
            var key = th.getAttribute('data-sort');
            var nextAsc = !(th.classList.contains('sorted') && th.classList.contains('sorted--asc'));
            ths.forEach(function (t) {
              t.classList.remove('sorted', 'sorted--asc', 'sorted--desc');
            });
            th.classList.add('sorted', nextAsc ? 'sorted--asc' : 'sorted--desc');
            render(key, nextAsc);
          });
        });
      }

      render('total_amount', false);
      setLoading(empEl, false);
    } catch (e) {
      empEl.innerHTML = '<p class="error">Ошибка загрузки сотрудников.</p>';
    }
  }

  function bindControls() {
    var summarySel = document.getElementById('summaryPeriodPlates');
    if (summarySel) summarySel.addEventListener('change', loadSummaryPlates);

    var dynSel = document.getElementById('dynamicsGroupPlates');
    if (dynSel) dynSel.addEventListener('change', loadDynamicsPlates);

    var empSel = document.getElementById('empPeriodPlates');
    if (empSel) empSel.addEventListener('change', loadEmployeesPlates);
  }

  function init() {
    bindControls();
    loadSummaryPlates();
    loadDynamicsPlates();
    loadEmployeesPlates();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();

