// Studio Sedillo – language switch (English / Nederlands). Elements carry both
// texts as data-en / data-nl. The choice is remembered on this device only, and only
// after the visitor taps a language button (so nothing is stored without asking).
(function () {
  'use strict';
  var LANGS = ['en', 'nl'];
  function start() {
    try {
      var asked = new URLSearchParams(location.search).get('lang');
      if (LANGS.indexOf(asked) >= 0) return asked;
      var saved = localStorage.getItem('studioSedillo_lang');
      if (LANGS.indexOf(saved) >= 0) return saved;
    } catch (e) { /* storage blocked */ }
    return String(navigator.language || 'en').slice(0, 2).toLowerCase() === 'nl' ? 'nl' : 'en';
  }
  function show(lang, remember) {
    document.documentElement.lang = lang;
    document.querySelectorAll('[data-' + lang + ']').forEach(function (el) { el.innerHTML = el.getAttribute('data-' + lang); });
    document.querySelectorAll('[data-title-' + lang + ']').forEach(function (el) { document.title = el.getAttribute('data-title-' + lang); });
    document.querySelectorAll('.langs button').forEach(function (b) { b.setAttribute('aria-pressed', String(b.dataset.lang === lang)); });
    if (remember) { try { localStorage.setItem('studioSedillo_lang', lang); } catch (e) { /* ignore */ } }
  }
  document.querySelectorAll('.langs button').forEach(function (b) {
    b.addEventListener('click', function () { show(b.dataset.lang, true); });
  });
  show(start());
})();
