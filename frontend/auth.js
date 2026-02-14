/**
 * Авторизация: токен в localStorage, заголовок для API, редирект на логин.
 */
(function () {
  var TOKEN_KEY = 'eye_w_token';
  var USER_KEY = 'eye_w_user';

  window.API_BASE_URL = window.API_BASE_URL || (window.location.hostname === 'localhost' ? 'http://localhost:8000' : '');

  window.getToken = function () { return localStorage.getItem(TOKEN_KEY); };
  window.setToken = function (token, user) {
    localStorage.setItem(TOKEN_KEY, token);
    if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  };
  window.clearAuth = function () {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
  };
  window.getUser = function () {
    try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); } catch (_) { return null; }
  };
  window.getAuthHeaders = function () {
    var h = { 'Content-Type': 'application/json' };
    var t = window.getToken();
    if (t) h['Authorization'] = 'Bearer ' + t;
    return h;
  };
  window.fetchWithAuth = function (url, options) {
    options = options || {};
    options.headers = options.headers || {};
    var t = window.getToken();
    if (t) options.headers['Authorization'] = 'Bearer ' + t;
    if (!options.headers['Content-Type']) options.headers['Content-Type'] = 'application/json';
    return fetch(url, options).then(function (res) {
      if (res.status === 401) { window.clearAuth(); window.location.href = 'login.html'; return Promise.reject(new Error('Требуется авторизация')); }
      return res;
    });
  };
  window.requireAuth = function () {
    if (!window.getToken() && !/login\.html$/i.test(window.location.pathname)) {
      window.location.href = 'login.html';
      return false;
    }
    return true;
  };
})();
