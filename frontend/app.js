/**
 * Павильон 1 — веб-форма операторов.
 * Документы выбираются из прейскуранта и добавляются в список; сумма считается автоматически.
 */

(function () {
  var API_BASE_URL = window.API_BASE_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');
  var fetchApi = window.fetchWithAuth || fetch;
  if (window.getToken && !window.getToken()) return;

  var priceList = [];
  var selectedDocuments = [];

  var el = function (id) { return document.getElementById(id); };

  var inputs = {
    clientFio: el('clientFio'),
    clientPassport: el('clientPassport'),
    clientAddress: el('clientAddress'),
    clientPhone: el('clientPhone'),
    clientComment: el('clientComment'),
    hasSeller: el('hasSeller'),
    sellerFio: el('sellerFio'),
    sellerPassport: el('sellerPassport'),
    sellerAddress: el('sellerAddress'),
    hasTrustee: el('hasTrustee'),
    trusteeFio: el('trusteeFio'),
    trusteePassport: el('trusteePassport'),
    trusteeBasis: el('trusteeBasis'),
    vin: el('vin'),
    brandModel: el('brandModel'),
    vehicleType: el('vehicleType'),
    year: el('year'),
    engine: el('engine'),
    chassis: el('chassis'),
    body: el('body'),
    color: el('color'),
    srts: el('srts'),
    plateNumber: el('plateNumber'),
    pts: el('pts'),
    stateDuty: el('stateDuty'),
    summaDkp: el('summaDkp')
  };

  var docSelect = el('docSelect');
  var btnAddDoc = el('btnAddDoc');
  var documentsList = el('documentsList');
  var documentsEmpty = el('documentsEmpty');
  var docList = el('docList');
  var summary = {
    sumStateDuty: el('sumStateDuty'),
    sumIncome: el('sumIncome'),
    sumTotal: el('sumTotal')
  };
  var preview = {
    previewFio: el('previewFio'),
    previewPassport: el('previewPassport'),
    previewAddress: el('previewAddress'),
    previewPhone: el('previewPhone'),
    previewSeller: el('previewSeller'),
    previewTrustee: el('previewTrustee'),
    previewVehicle: el('previewVehicle'),
    previewService: el('previewService'),
    previewSummaDkp: el('previewSummaDkp'),
    previewTotal: el('previewTotal')
  };
  var btnAcceptCash = el('btnAcceptCash');
  var btnPrint = el('btnPrint');
  var orderIdDisplay = el('orderIdDisplay');
  var currentTime = el('currentTime');

  function num(val) {
    var n = parseFloat(val);
    return isNaN(n) ? 0 : Math.max(0, n);
  }

  function getStateDuty() {
    return num(inputs.stateDuty && inputs.stateDuty.value);
  }

  function getDocumentsTotal() {
    return selectedDocuments.reduce(function (sum, d) { return sum + num(d.price); }, 0);
  }

  function getTotal() {
    return getStateDuty() + getDocumentsTotal();
  }

  function formatMoney(value) {
    return new Intl.NumberFormat('ru-RU', { style: 'decimal', minimumFractionDigits: 0 }).format(value) + ' ₽';
  }

  function renderDocumentsList() {
    if (documentsEmpty) documentsEmpty.style.display = selectedDocuments.length ? 'none' : 'block';
    if (!documentsList) return;
    documentsList.innerHTML = selectedDocuments.map(function (d, i) {
      return '<li class="documents-to-print__item">' +
        '<span class="documents-to-print__item-info">' +
          '<span>' + (d.label || d.template) + '</span>' +
          '<span class="documents-to-print__item-price">' + formatMoney(num(d.price)) + '</span>' +
        '</span>' +
        '<button type="button" class="documents-to-print__item-remove" data-index="' + i + '">Удалить</button>' +
      '</li>';
    }).join('');
    documentsList.querySelectorAll('.documents-to-print__item-remove').forEach(function (btn) {
      btn.addEventListener('click', function () {
        var idx = parseInt(btn.getAttribute('data-index'), 10);
        selectedDocuments.splice(idx, 1);
        renderDocumentsList();
        syncFromMainForm();
      });
    });
  }

  function updateSummary() {
    var duty = getStateDuty();
    var income = getDocumentsTotal();
    var total = getTotal();
    if (summary.sumStateDuty) summary.sumStateDuty.textContent = formatMoney(duty);
    if (summary.sumIncome) summary.sumIncome.textContent = formatMoney(income);
    if (summary.sumTotal) summary.sumTotal.textContent = formatMoney(total);
    var canPay = total > 0 && inputs.clientFio && inputs.clientFio.value.trim() && selectedDocuments.length > 0;
    if (btnAcceptCash) btnAcceptCash.disabled = !canPay;
    if (btnPrint) btnPrint.disabled = !canPay;
  }

  function updatePreview() {
    var fio = (inputs.clientFio && inputs.clientFio.value.trim()) || '—';
    var passport = (inputs.clientPassport && inputs.clientPassport.value.trim()) || '—';
    var address = (inputs.clientAddress && inputs.clientAddress.value.trim()) || '—';
    var phone = (inputs.clientPhone && inputs.clientPhone.value.trim()) || '—';
    var seller = '—';
    if (inputs.hasSeller && inputs.hasSeller.checked && inputs.sellerFio && inputs.sellerFio.value.trim()) {
      seller = [inputs.sellerFio.value.trim(), inputs.sellerPassport && inputs.sellerPassport.value.trim(), inputs.sellerAddress && inputs.sellerAddress.value.trim()].filter(Boolean).join(', ');
    }
    var trustee = '—';
    if (inputs.hasTrustee && inputs.hasTrustee.checked && inputs.trusteeFio && inputs.trusteeFio.value.trim()) {
      trustee = [inputs.trusteeFio.value.trim(), inputs.trusteePassport && inputs.trusteePassport.value.trim(), inputs.trusteeBasis && inputs.trusteeBasis.value.trim()].filter(Boolean).join(' · ');
    }
    var vehicle = (inputs.vin && inputs.vin.value.trim()) || (inputs.brandModel && inputs.brandModel.value.trim()) ? [inputs.vin && inputs.vin.value.trim(), inputs.brandModel && inputs.brandModel.value.trim()].filter(Boolean).join(' · ') : '—';
    var docLabels = selectedDocuments.length ? selectedDocuments.map(function (d) { return d.label || d.template; }).join(', ') : '—';
    var summaDkpVal = (inputs.summaDkp && num(inputs.summaDkp.value) > 0) ? formatMoney(num(inputs.summaDkp.value)) : '—';
    if (preview.previewFio) preview.previewFio.textContent = fio;
    if (preview.previewPassport) preview.previewPassport.textContent = passport;
    if (preview.previewAddress) preview.previewAddress.textContent = address;
    if (preview.previewPhone) preview.previewPhone.textContent = phone;
    if (preview.previewSeller) preview.previewSeller.textContent = seller;
    if (preview.previewTrustee) preview.previewTrustee.textContent = trustee;
    if (preview.previewVehicle) preview.previewVehicle.textContent = vehicle;
    if (preview.previewService) preview.previewService.textContent = docLabels;
    if (preview.previewSummaDkp) preview.previewSummaDkp.textContent = summaDkpVal;
    if (preview.previewTotal) preview.previewTotal.textContent = formatMoney(getTotal());
  }

  function updateDocList() {
    if (!docList) return;
    if (!selectedDocuments.length) {
      docList.innerHTML = '<li class="doc-list__item doc-list__item--placeholder">Добавьте документы выше — здесь будет тот же список</li>';
      return;
    }
    docList.innerHTML = selectedDocuments.map(function (d) {
      return '<li class="doc-list__item">' + (d.label || d.template) + '</li>';
    }).join('');
  }

  function syncFromMainForm() {
    updateSummary();
    updatePreview();
    updateDocList();
  }

  function addSelectedDocument() {
    if (!docSelect || !docSelect.value) return;
    var template = docSelect.value;
    var item = priceList.find(function (p) { return p.template === template; });
    if (!item) return;
    selectedDocuments.push({
      template: item.template,
      label: item.label || item.template,
      price: item.price
    });
    renderDocumentsList();
    syncFromMainForm();
  }

  function buildOrderPayload() {
    var user = window.getUser();
    var employeeId = user && user.id ? user.id : null;
    var needPlate = selectedDocuments.some(function (d) { return d.template === 'number.docx'; });
    return {
      client_fio: (inputs.clientFio && inputs.clientFio.value.trim()) || null,
      client_passport: (inputs.clientPassport && inputs.clientPassport.value.trim()) || null,
      client_address: (inputs.clientAddress && inputs.clientAddress.value.trim()) || null,
      client_phone: (inputs.clientPhone && inputs.clientPhone.value.trim()) || null,
      client_comment: (inputs.clientComment && inputs.clientComment.value.trim()) || null,
      seller_fio: (inputs.hasSeller && inputs.hasSeller.checked && inputs.sellerFio && inputs.sellerFio.value.trim()) ? inputs.sellerFio.value.trim() : null,
      seller_passport: (inputs.hasSeller && inputs.hasSeller.checked && inputs.sellerPassport && inputs.sellerPassport.value.trim()) ? inputs.sellerPassport.value.trim() : null,
      seller_address: (inputs.hasSeller && inputs.hasSeller.checked && inputs.sellerAddress && inputs.sellerAddress.value.trim()) ? inputs.sellerAddress.value.trim() : null,
      trustee_fio: (inputs.hasTrustee && inputs.hasTrustee.checked && inputs.trusteeFio && inputs.trusteeFio.value.trim()) ? inputs.trusteeFio.value.trim() : null,
      trustee_passport: (inputs.hasTrustee && inputs.hasTrustee.checked && inputs.trusteePassport && inputs.trusteePassport.value.trim()) ? inputs.trusteePassport.value.trim() : null,
      trustee_basis: (inputs.hasTrustee && inputs.hasTrustee.checked && inputs.trusteeBasis && inputs.trusteeBasis.value.trim()) ? inputs.trusteeBasis.value.trim() : null,
      vin: (inputs.vin && inputs.vin.value.trim()) || null,
      brand_model: (inputs.brandModel && inputs.brandModel.value.trim()) || null,
      vehicle_type: (inputs.vehicleType && inputs.vehicleType.value.trim()) || null,
      year: (inputs.year && inputs.year.value.trim()) || null,
      engine: (inputs.engine && inputs.engine.value.trim()) || null,
      chassis: (inputs.chassis && inputs.chassis.value.trim()) || null,
      body: (inputs.body && inputs.body.value.trim()) || null,
      color: (inputs.color && inputs.color.value.trim()) || null,
      srts: (inputs.srts && inputs.srts.value.trim()) || null,
      plate_number: (inputs.plateNumber && inputs.plateNumber.value.trim()) || null,
      pts: (inputs.pts && inputs.pts.value.trim()) || null,
      service_type: selectedDocuments[0] ? selectedDocuments[0].template : null,
      need_plate: needPlate,
      state_duty: getStateDuty(),
      extra_amount: 0,
      plate_amount: 0,
      summa_dkp: inputs.summaDkp ? num(inputs.summaDkp.value) : 0,
      employee_id: employeeId || null,
      documents: selectedDocuments.map(function (d) {
        return { template: d.template, price: num(d.price), label: d.label || d.template };
      })
    };
  }

  function showError(msg) {
    alert('Ошибка: ' + msg);
  }

  async function acceptCash() {
    var total = getTotal();
    if (total <= 0) return;
    btnAcceptCash.disabled = true;
    btnAcceptCash.textContent = 'Отправка…';
    try {
      var resOrder = await fetchApi(API_BASE_URL + '/orders', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(buildOrderPayload())
      });
      if (!resOrder.ok) {
        var err = await resOrder.json().catch(function () { return { detail: resOrder.statusText }; });
        throw new Error(err.detail || JSON.stringify(err));
      }
      var order = await resOrder.json();
      var resPay = await fetchApi(API_BASE_URL + '/orders/' + order.id + '/pay', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!resPay.ok) {
        var errPay = await resPay.json().catch(function () { return { detail: resPay.statusText }; });
        throw new Error(errPay.detail || JSON.stringify(errPay));
      }
      orderIdDisplay.textContent = 'Заказ: ' + (order.public_id || order.id);
      orderIdDisplay.style.fontWeight = '600';
      btnAcceptCash.textContent = 'Оплата принята';
      window.lastOrderId = order.id;
      window.lastOrderDocuments = selectedDocuments.map(function (d) { return d.template; });
    } catch (e) {
      btnAcceptCash.disabled = false;
      btnAcceptCash.textContent = 'Принять наличные';
      showError(e.message || 'Не удалось создать заказ');
    }
  }

  function doPrint() {
    var orderId = window.lastOrderId;
    if (!orderId) {
      alert('Сначала примите оплату по заказу (кнопка «Принять наличные»).');
      return;
    }
    var templates = window.lastOrderDocuments || [];
    if (!templates.length) {
      alert('Нет списка документов по последнему заказу.');
      return;
    }
    templates.forEach(function (template) {
      var url = API_BASE_URL + '/orders/' + orderId + '/documents/' + encodeURIComponent(template);
      fetchApi(url).then(function (r) { return r.blob(); }).then(function (blob) {
        var u = URL.createObjectURL(blob);
        window.open(u, '_blank', 'noopener');
      });
    });
  }

  function updateTime() {
    if (currentTime) {
      currentTime.textContent = new Date().toLocaleString('ru-RU', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
    }
  }

  function bindInputs() {
    Object.keys(inputs).forEach(function (key) {
      var node = inputs[key];
      if (!node) return;
      node.addEventListener('input', syncFromMainForm);
      node.addEventListener('change', syncFromMainForm);
    });
  }

  async function loadPriceList() {
    try {
      var r = await fetchApi(API_BASE_URL + '/price-list');
      if (!r.ok) throw new Error(r.statusText);
      priceList = await r.json();
      if (!Array.isArray(priceList)) priceList = [];
      if (docSelect) {
        docSelect.innerHTML = '<option value="">Выберите документ из списка</option>' +
          priceList.map(function (p) {
            var price = typeof p.price === 'number' ? p.price : parseFloat(p.price);
            var label = (p.label || p.template) + ' — ' + (isNaN(price) ? '0' : price) + ' ₽';
            return '<option value="' + (p.template || '').replace(/"/g, '&quot;') + '">' + (label.replace(/</g, '&lt;')) + '</option>';
          }).join('');
      }
    } catch (e) {
      if (docSelect) docSelect.innerHTML = '<option value="">Не удалось загрузить прейскурант</option>';
    }
  }

  function setupTogglableSections() {
    var sellerBody = el('sellerBody');
    var trusteeBody = el('trusteeBody');
    if (inputs.hasSeller && sellerBody) {
      sellerBody.classList.toggle('form-section__body--closed', !inputs.hasSeller.checked);
      inputs.hasSeller.addEventListener('change', function () {
        sellerBody.classList.toggle('form-section__body--closed', !inputs.hasSeller.checked);
      });
    }
    if (inputs.hasTrustee && trusteeBody) {
      trusteeBody.classList.toggle('form-section__body--closed', !inputs.hasTrustee.checked);
      inputs.hasTrustee.addEventListener('change', function () {
        trusteeBody.classList.toggle('form-section__body--closed', !inputs.hasTrustee.checked);
      });
    }
  }

  async function init() {
    await loadPriceList();
    bindInputs();
    setupTogglableSections();
    renderDocumentsList();
    syncFromMainForm();
    updateTime();
    setInterval(updateTime, 60000);
    if (btnAddDoc) btnAddDoc.addEventListener('click', addSelectedDocument);
    if (docSelect) docSelect.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); addSelectedDocument(); } });
    if (btnAcceptCash) btnAcceptCash.addEventListener('click', acceptCash);
    if (btnPrint) btnPrint.addEventListener('click', doPrint);
  }

  init();
})();
