/**
 * Павильон 1 — веб-форма операторов.
 * Одна основная форма: при изменении полей автоматически заполняются
 * блоки «Итого», «Сводка для документов» и список документов для печати.
 */

(function () {
  const SERVICE_LABELS = {
    mreo: 'МРЭО (постановка/снятие)',
    dkp: 'ДКП',
    dkp_dar: 'ДКП дарение',
    dkp_pieces: 'ДКП запчасти',
    doverennost: 'Доверенность',
    zaiavlenie: 'Заявление',
    akt_pp: 'Акт приёма-передачи',
    prokuratura: 'Прокуратура'
  };

  const SERVICE_DOCS = {
    mreo: ['mreo.docx'],
    dkp: ['DKP.docx'],
    dkp_dar: ['dkp_dar.docx'],
    dkp_pieces: ['dkp_pieces.docx'],
    doverennost: ['doverennost.docx'],
    zaiavlenie: ['zaiavlenie.docx'],
    akt_pp: ['akt_pp.docx'],
    prokuratura: ['prokuratura.docx']
  };

  const el = (id) => document.getElementById(id);

  const inputs = {
    clientFio: el('clientFio'),
    clientPassport: el('clientPassport'),
    clientAddress: el('clientAddress'),
    clientPhone: el('clientPhone'),
    clientComment: el('clientComment'),
    sellerFio: el('sellerFio'),
    sellerPassport: el('sellerPassport'),
    sellerAddress: el('sellerAddress'),
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
    serviceType: el('serviceType'),
    needPlate: el('needPlate'),
    stateDuty: el('stateDuty'),
    extraAmount: el('extraAmount'),
    plateAmount: el('plateAmount'),
    summaDkp: el('summaDkp')
  };

  const summary = {
    sumStateDuty: el('sumStateDuty'),
    sumIncome: el('sumIncome'),
    sumTotal: el('sumTotal')
  };

  const preview = {
    previewFio: el('previewFio'),
    previewPassport: el('previewPassport'),
    previewAddress: el('previewAddress'),
    previewPhone: el('previewPhone'),
    previewSeller: el('previewSeller'),
    previewVehicle: el('previewVehicle'),
    previewService: el('previewService'),
    previewPlate: el('previewPlate'),
    previewSummaDkp: el('previewSummaDkp'),
    previewTotal: el('previewTotal')
  };

  const docList = el('docList');
  const btnAcceptCash = el('btnAcceptCash');
  const btnPrint = el('btnPrint');
  const orderIdDisplay = el('orderIdDisplay');
  const currentTime = el('currentTime');
  const operatorName = el('operatorName');

  function num(val) {
    const n = parseFloat(val);
    return isNaN(n) ? 0 : Math.max(0, n);
  }

  function getStateDuty() {
    return num(inputs.stateDuty.value);
  }

  function getExtraAmount() {
    return num(inputs.extraAmount.value);
  }

  function getPlateAmount() {
    return inputs.needPlate.value === 'yes' ? num(inputs.plateAmount.value) : 0;
  }

  function getIncome() {
    return getExtraAmount() + getPlateAmount();
  }

  function getTotal() {
    return getStateDuty() + getIncome();
  }

  function formatMoney(value) {
    return new Intl.NumberFormat('ru-RU', { style: 'decimal', minimumFractionDigits: 0 }).format(value) + ' ₽';
  }

  function updateSummary() {
    const duty = getStateDuty();
    const income = getIncome();
    const total = getTotal();

    summary.sumStateDuty.textContent = formatMoney(duty);
    summary.sumIncome.textContent = formatMoney(income);
    summary.sumTotal.textContent = formatMoney(total);

    const canPay = total > 0 && inputs.clientFio.value.trim() && inputs.serviceType.value;
    btnAcceptCash.disabled = !canPay;
    btnPrint.disabled = !canPay;
  }

  function updatePreview() {
    const fio = (inputs.clientFio && inputs.clientFio.value.trim()) || '—';
    const passport = (inputs.clientPassport && inputs.clientPassport.value.trim()) || '—';
    const address = (inputs.clientAddress && inputs.clientAddress.value.trim()) || '—';
    const phone = (inputs.clientPhone && inputs.clientPhone.value.trim()) || '—';
    const seller = (inputs.sellerFio && inputs.sellerFio.value.trim()) ? [inputs.sellerFio.value.trim(), inputs.sellerPassport && inputs.sellerPassport.value.trim(), inputs.sellerAddress && inputs.sellerAddress.value.trim()].filter(Boolean).join(', ') : '—';
    const vehicle = (inputs.vin && inputs.vin.value.trim()) || (inputs.brandModel && inputs.brandModel.value.trim()) ? [inputs.vin && inputs.vin.value.trim(), inputs.brandModel && inputs.brandModel.value.trim()].filter(Boolean).join(' · ') : '—';
    const serviceKey = inputs.serviceType.value;
    const serviceLabel = serviceKey ? (SERVICE_LABELS[serviceKey] || serviceKey) : '—';
    const plateLabel = inputs.needPlate.value === 'yes' ? 'Изготовить' : 'Не нужен';
    const summaDkpVal = inputs.summaDkp && num(inputs.summaDkp.value) > 0 ? formatMoney(num(inputs.summaDkp.value)) : '—';

    if (preview.previewFio) preview.previewFio.textContent = fio;
    if (preview.previewPassport) preview.previewPassport.textContent = passport;
    if (preview.previewAddress) preview.previewAddress.textContent = address;
    if (preview.previewPhone) preview.previewPhone.textContent = phone;
    if (preview.previewSeller) preview.previewSeller.textContent = seller;
    if (preview.previewVehicle) preview.previewVehicle.textContent = vehicle;
    if (preview.previewService) preview.previewService.textContent = serviceLabel;
    if (preview.previewPlate) preview.previewPlate.textContent = plateLabel;
    if (preview.previewSummaDkp) preview.previewSummaDkp.textContent = summaDkpVal;
    if (preview.previewTotal) preview.previewTotal.textContent = formatMoney(getTotal());
  }

  function updateDocList() {
    const serviceKey = inputs.serviceType.value;
    const withPlate = inputs.needPlate.value === 'yes';

    if (!serviceKey) {
      docList.innerHTML = '<li class="doc-list__item doc-list__item--placeholder">Выберите тип услуги — список заполнится автоматически</li>';
      return;
    }

    const docs = [...(SERVICE_DOCS[serviceKey] || [])];
    if (withPlate) docs.push('number.docx');

    docList.innerHTML = docs.map((d) => `<li class="doc-list__item">${d}</li>`).join('');
  }

  function syncFromMainForm() {
    updateSummary();
    updatePreview();
    updateDocList();
  }

  function togglePlateAmount() {
    const needPlate = inputs.needPlate.value === 'yes';
    inputs.plateAmount.disabled = !needPlate;
    if (!needPlate) inputs.plateAmount.value = '0';
    syncFromMainForm();
  }

  function bindInputs() {
    Object.values(inputs).forEach((node) => {
      if (!node) return;
      node.addEventListener('input', syncFromMainForm);
      node.addEventListener('change', syncFromMainForm);
    });
    inputs.needPlate.addEventListener('change', togglePlateAmount);
  }

  function acceptCash() {
    const total = getTotal();
    if (total <= 0) return;

    const orderId = 'ORD-' + Date.now();
    orderIdDisplay.textContent = 'Заказ: ' + orderId;
    orderIdDisplay.style.fontWeight = '600';

    btnAcceptCash.disabled = true;
    btnAcceptCash.textContent = 'Оплата принята';

    // Здесь потом будет вызов API: POST /orders, POST /payments
    console.log('Order created:', orderId, { total, stateDuty: getStateDuty(), income: getIncome() });
  }

  function doPrint() {
    window.print();
  }

  function initOperator() {
    const name = localStorage.getItem('pavilion_operator_name') || '';
    operatorName.textContent = name || '—';
  }

  function setOperator() {
    const name = prompt('Имя оператора:', localStorage.getItem('pavilion_operator_name') || '');
    if (name != null) {
      const trimmed = String(name).trim();
      localStorage.setItem('pavilion_operator_name', trimmed);
      operatorName.textContent = trimmed || '—';
    }
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

  function init() {
    bindInputs();
    togglePlateAmount();
    syncFromMainForm();
    initOperator();
    updateTime();
    setInterval(updateTime, 60000);

    if (btnAcceptCash) btnAcceptCash.addEventListener('click', acceptCash);
    if (btnPrint) btnPrint.addEventListener('click', doPrint);
    const btnSetOperator = el('btnSetOperator');
    if (btnSetOperator) btnSetOperator.addEventListener('click', setOperator);
  }

  init();
})();
