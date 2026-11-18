/* Collection navigation uses native disclosures and keeps old product links valid. */
(function () {
  'use strict';

  var oldProductAnchors = ['#ssamssam', '#hotssam', '#tossam', '#gossam'];
  if (/^\/products\/?$/.test(location.pathname) && oldProductAnchors.indexOf(location.hash.toLowerCase()) !== -1) {
    var lang = new URLSearchParams(location.search).get('lang');
    var destination = '/products/ssamssam/' + (lang === 'en' || lang === 'ko' ? '?lang=' + lang : '') + location.hash;
    location.replace(destination);
    return;
  }

  function init() {
    var menus = Array.prototype.slice.call(document.querySelectorAll('.nav-collections'));
    var nav = document.getElementById('nav');
    var burger = document.getElementById('burger');

    function closeMenus(except) {
      menus.forEach(function (menu) {
        if (menu !== except) menu.open = false;
      });
    }

    menus.forEach(function (menu) {
      menu.addEventListener('toggle', function () {
        if (menu.open) closeMenus(menu);
      });
      menu.addEventListener('focusout', function () {
        setTimeout(function () {
          if (!menu.contains(document.activeElement)) menu.open = false;
        }, 0);
      });
      menu.querySelectorAll('a').forEach(function (link) {
        link.addEventListener('click', function () { closeMenus(); });
      });
    });

    document.addEventListener('pointerdown', function (event) {
      menus.forEach(function (menu) {
        if (!menu.contains(event.target)) menu.open = false;
      });
      if (nav && burger && nav.classList.contains('open') && !nav.contains(event.target) && !burger.contains(event.target)) {
        nav.classList.remove('open');
        burger.setAttribute('aria-expanded', 'false');
      }
    });

    document.addEventListener('keydown', function (event) {
      if (event.key !== 'Escape') return;
      var openMenu = menus.find(function (menu) { return menu.open; });
      if (openMenu) {
        event.preventDefault();
        openMenu.open = false;
        var summary = openMenu.querySelector('summary');
        if (summary) summary.focus();
      } else if (nav && burger && nav.classList.contains('open')) {
        event.preventDefault();
        nav.classList.remove('open');
        burger.setAttribute('aria-expanded', 'false');
        burger.focus();
      }
    });

    if (nav) {
      nav.querySelectorAll('a').forEach(function (link) {
        link.addEventListener('click', function () { closeMenus(); });
      });
    }
    if (burger) {
      burger.addEventListener('click', function () {
        if (burger.getAttribute('aria-expanded') === 'false') closeMenus();
      });
    }
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
  else init();
})();
