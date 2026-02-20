/**
 * Главная страница: шапка (павильон, меню), контент P1/P2, последние заявки, список номеров.
 */
(function () {
  if (!window.requireAuth()) return;
  var API = window.API_BASE_URL || '';
  var fetchApi = window.fetchWithAuth || fetch;

  var me = window.getMe();
  if (!me || !me.menu_items) {
    window.loadMe().then(function (m) {
      me = m;
      if (me) initDashboard();
    });
    return;
  }
  initDashboard();

  function initDashboard() {
    renderHeader();
    setPavilionVisibility();
    switchContent(window.getCurrentPavilion());
    var btnQuick = document.getElementById('btnQuickCreate');
    if (btnQuick) btnQuick.addEventListener('click', scrollToForm);
    var btnMenu = document.getElementById('btnMenu');
    if (btnMenu) btnMenu.addEventListener('click', function (e) { e.stopPropagation(); toggleMenu(); });
    var userNameEl = document.getElementById('headerUserName');
    if (userNameEl) {
      userNameEl.addEventListener('click', function (e) { e.stopPropagation(); toggleMenu(); });
    }
    document.getElementById('pavilionSelect').addEventListener('change', onPavilionChange);
    document.addEventListener('click', function (e) {
      if (!e.target.closest('.header__menu-wrap')) {
        var dd = document.getElementById('menuDropdown');
        if (dd) dd.setAttribute('aria-hidden', 'true');
      }
    });
    loadLast10Orders();
  }

  function renderHeader() {
    var userNameEl = document.getElementById('headerUserName');
    if (userNameEl) userNameEl.textContent = me.name || me.login || 'Аккаунт';

    var allowed = me.allowed_pavilions || [1];
    var pavLabel = document.getElementById('pavilionLabel');
    var pavSelect = document.getElementById('pavilionSelect');
    if (allowed.length > 1) {
      pavLabel.style.display = 'none';
      pavSelect.style.display = 'inline-block';
      pavSelect.innerHTML = '';
      if (allowed.indexOf(1) >= 0) {
        var o1 = document.createElement('option');
        o1.value = '1';
        o1.textContent = 'Павильон 1 — Документы';
        pavSelect.appendChild(o1);
      }
      if (allowed.indexOf(2) >= 0) {
        var o2 = document.createElement('option');
        o2.value = '2';
        o2.textContent = 'Павильон 2 — Номера';
        pavSelect.appendChild(o2);
      }
      pavSelect.value = String(window.getCurrentPavilion());
    } else {
      pavLabel.textContent = allowed[0] === 2 ? 'Павильон 2 — Номера' : 'Павильон 1 — Документы';
    }

    var canForm = (me.role === 'ROLE_OPERATOR' || me.role === 'ROLE_MANAGER' || me.role === 'ROLE_ADMIN');
    var btnQuick = document.getElementById('btnQuickCreate');
    if (btnQuick) btnQuick.style.display = (canForm && window.getCurrentPavilion() === 1) ? 'inline-block' : 'none';

    var inner = document.getElementById('menuDropdownInner');
    inner.innerHTML = '';
    (me.menu_items || []).forEach(function (item) {
      if (item.divider) {
        inner.appendChild(document.createElement('hr'));
        return;
      }
      var a = document.createElement('a');
      a.href = item.href || '#';
      a.textContent = item.label;
      a.setAttribute('data-action', item.action || '');
      a.setAttribute('data-id', item.id || '');
      a.addEventListener('click', function (e) {
        if (item.action === 'logout') {
          e.preventDefault();
          window.clearAuth();
          window.location.href = 'login.html';
          return;
        }
        if (item.action === 'change_password') {
          e.preventDefault();
          window.location.href = 'account.html';
          return;
        }
        document.getElementById('menuDropdown').setAttribute('aria-hidden', 'true');
      });
      inner.appendChild(a);
    });
  }

  function setPavilionVisibility() {
    var allowed = me.allowed_pavilions || [1];
    document.getElementById('pavilionWrap').style.display = allowed.length ? 'block' : 'none';
  }

  function toggleMenu() {
    var dd = document.getElementById('menuDropdown');
    if (!dd) return;
    var isOpen = dd.getAttribute('aria-hidden') !== 'true';
    dd.setAttribute('aria-hidden', isOpen ? 'true' : 'false');
  }

  function onPavilionChange() {
    var sel = document.getElementById('pavilionSelect');
    var p = parseInt(sel.value, 10);
    if (p === 1 || p === 2) {
      window.setCurrentPavilion(p);
      switchContent(p);
      renderHeader();
      if (p === 2) loadPlateList();
    }
  }

  function switchContent(pavilion) {
    document.getElementById('contentP1').style.display = pavilion === 1 ? 'block' : 'none';
    document.getElementById('contentP2').style.display = pavilion === 2 ? 'block' : 'none';
    if (pavilion === 2) loadPlateList();
  }

  function scrollToForm() {
    var el = document.getElementById('mainForm');
    if (el) el.scrollIntoView({ behavior: 'smooth' });
  }

  function loadLast10Orders() {
    if (window.getCurrentPavilion() !== 1) return;
    fetchApi(API + '/orders?pavilion=1&limit=10')
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (orders) {
        var loading = document.getElementById('lastOrdersLoading');
        var table = document.getElementById('lastOrdersTable');
        var body = document.getElementById('lastOrdersBody');
        var empty = document.getElementById('lastOrdersEmpty');
        if (!body) return;
        loading.style.display = 'none';
        if (!orders || orders.length === 0) {
          empty.style.display = 'block';
          return;
        }
        table.style.display = 'table';
        body.innerHTML = orders.map(function (o) {
          var client = (o.client && String(o.client).trim()) ? escapeHtml(o.client) : '—';
          var sum = (o.total_amount != null) ? formatMoney(o.total_amount) : '—';
          var date = (o.created_at || '').slice(0, 10);
          return '<tr><td>' + (o.public_id || o.id) + '</td><td>' + client + '</td><td>' + sum + '</td><td>' + (o.status || '') + '</td><td>' + date + '</td></tr>';
        }).join('');
      })
      .catch(function () {
        document.getElementById('lastOrdersLoading').textContent = 'Ошибка загрузки';
      });
  }

  function formatMoney(n) {
    return new Intl.NumberFormat('ru-RU', { minimumFractionDigits: 0 }).format(n) + ' ₽';
  }
  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  var STATUS_LABELS = { PAID: 'Оплачен', PLATE_IN_PROGRESS: 'В работе', PLATE_READY: 'Готов', PROBLEM: 'Проблема', COMPLETED: 'Завершён' };
  var CAN_ISSUE = ['PAID', 'PLATE_IN_PROGRESS', 'PLATE_READY'];
  var CAN_DELETE = ['PAID', 'PLATE_IN_PROGRESS', 'PLATE_READY'];

  function loadPlateList() {
    var container = document.getElementById('plateListContainer');
    if (!container) return;
    document.getElementById('plateListLoading').style.display = 'block';
    document.getElementById('plateOrderTable').style.display = 'none';
    document.getElementById('plateListEmpty').style.display = 'none';
    fetchApi(API + '/orders/plate-list')
      .then(function (r) { return r.ok ? r.json() : []; })
      .then(function (orders) {
        var loading = document.getElementById('plateListLoading');
        var table = document.getElementById('plateOrderTable');
        var body = document.getElementById('plateOrderBody');
        var empty = document.getElementById('plateListEmpty');
        loading.style.display = 'none';
        if (!orders || orders.length === 0) {
          empty.style.display = 'block';
          return;
        }
        table.style.display = 'table';
        body.innerHTML = orders.map(function (o) {
          var clientEsc = escapeHtml((o.client || '—'));
          var plateAmt = o.plate_amount != null ? o.plate_amount : o.total_amount;
          var issueBtn = CAN_ISSUE.indexOf(o.status) >= 0 ? '<button type="button" class="btn btn-sm btn--primary" data-order="' + o.id + '" data-status="COMPLETED" data-client="' + clientEsc + '" data-amount="' + (plateAmt || 0) + '">Выдано</button>' : '';
          var sep = (issueBtn && CAN_DELETE.indexOf(o.status) >= 0) ? ' ' : '';
          var deleteBtn = CAN_DELETE.indexOf(o.status) >= 0 ? '<button type="button" class="btn btn-sm btn--danger-like" data-order="' + o.id + '" data-status="PROBLEM" data-delete="1">Удалить</button>' : '';
          var payBtn = (o.debt || 0) > 0 ? '<button type="button" class="btn btn-sm btn--secondary" data-order="' + o.id + '" data-public-id="' + (o.public_id || o.id) + '" data-pay="1">Доплата</button>' : '';
          var docLink = '<a href="#" class="doc-link" data-order-id="' + o.id + '" data-doc="zaiavlenie_na_nomera.docx">📄</a>';
          return '<tr><td>' + (o.public_id || o.id) + '</td><td>' + (o.client || '—') + '</td><td>' + formatMoney(o.plate_amount != null ? o.plate_amount : o.total_amount) + '</td><td>' + docLink + '</td><td><span class="status status-' + o.status + '">' + (STATUS_LABELS[o.status] || o.status) + '</span></td><td><div class="btn-group">' + issueBtn + sep + deleteBtn + payBtn + '</div></td></tr>';
        }).join('');
        bindPlateActions();
      })
      .catch(function () {
        document.getElementById('plateListLoading').textContent = 'Ошибка загрузки';
      });
  }

  function bindPlateActions() {
    var body = document.getElementById('plateOrderBody');
    if (!body) return;
    body.querySelectorAll('[data-status]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = parseInt(btn.getAttribute('data-order'), 10);
        var status = btn.getAttribute('data-status');
        var isDelete = btn.getAttribute('data-delete') === '1';
        var clientName = (btn.getAttribute('data-client') || '').replace(/&quot;/g, '"').replace(/&lt;/g, '<');
        var plateAmount = parseFloat(btn.getAttribute('data-amount')) || 0;
        if (isDelete && !confirm('Удалить заказ из списка? Статус будет «Проблема».')) return;
        fetchApi(API + '/orders/' + id + '/status', { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: status }) })
          .then(function (r) { if (!r.ok) throw new Error('Ошибка'); return r.json(); })
          .then(function () {
            if (status === 'COMPLETED' && plateAmount > 0) {
              return fetchApi(API + '/cash/plate-rows', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ client_name: clientName || '—', amount: plateAmount }) })
                .then(function (pr) { if (!pr.ok) throw new Error('Касса'); return pr; })
                .catch(function () { loadPlateList(); alert('Статус обновлён. Строку в кассу номеров добавьте вручную.'); });
            }
          })
          .then(function () { loadPlateList(); })
          .catch(function (e) { alert(e.message || 'Ошибка'); loadPlateList(); });
      });
    });
    body.querySelectorAll('[data-pay]').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var id = parseInt(btn.getAttribute('data-order'), 10);
        document.getElementById('modalOrderIdP2').textContent = btn.getAttribute('data-public-id') || id;
        document.getElementById('modalAmountP2').value = '';
        document.getElementById('modalPay').style.display = 'flex';
        document.getElementById('modalPay').dataset.orderId = id;
      });
    });
    body.querySelectorAll('.doc-link').forEach(function (a) {
      a.addEventListener('click', function (e) {
        e.preventDefault();
        var orderId = parseInt(a.getAttribute('data-order-id'), 10);
        fetchApi(API + '/orders/' + orderId + '/documents/zaiavlenie_na_nomera.docx').then(function (r) {
          if (!r.ok) throw new Error('Документ');
          return r.blob();
        }).then(function (blob) {
          window.open(URL.createObjectURL(blob), '_blank');
        }).catch(function () { alert('Не удалось открыть документ'); });
      });
    });
  }

  document.getElementById('modalSubmitP2').addEventListener('click', function () {
    var id = document.getElementById('modalPay').dataset.orderId;
    var amount = parseFloat(document.getElementById('modalAmountP2').value) || 0;
    if (amount <= 0) { alert('Введите сумму'); return; }
    fetchApi(API + '/orders/' + id + '/pay-extra', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ amount: amount }) })
      .then(function (r) { if (!r.ok) return r.json().then(function (j) { throw new Error(j.detail || 'Ошибка'); }); })
      .then(function () {
        document.getElementById('modalPay').style.display = 'none';
        loadPlateList();
      })
      .catch(function (e) { alert(e.message || 'Ошибка'); });
  });
  document.getElementById('modalCancelP2').addEventListener('click', function () {
    document.getElementById('modalPay').style.display = 'none';
  });
})();
