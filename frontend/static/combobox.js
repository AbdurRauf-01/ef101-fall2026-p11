// Type-to-filter drop-down for text boxes that have a <datalist> (CPU and CPU family on the Add / Edit form).
// It draws the list in the app's own style, like the other drop-downs. Without JavaScript the browser's own
// datalist still works. The list only suggests: anything else can still be typed, and the server checks on Save.
(function () {
  var MAX = 120;

  function norm(s) { return (s || '').toLowerCase().replace(/[\s\-_]+/g, ''); }

  function build(input) {
    var dl = document.getElementById(input.getAttribute('list') || '');
    if (!dl) return;
    var items = Array.prototype.map.call(dl.options, function (o) { return o.value; });
    input.removeAttribute('list');                        // stops the browser drawing its own list as well

    var wrap = document.createElement('div');
    wrap.className = 'combo';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);

    var btn = document.createElement('button');
    btn.type = 'button'; btn.tabIndex = -1; btn.className = 'combo-btn';
    btn.setAttribute('aria-label', 'Show the list');
    btn.innerHTML = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><polyline points="6 9 12 15 18 9"></polyline></svg>';
    wrap.appendChild(btn);

    var list = document.createElement('ul');
    list.className = 'combo-list'; list.id = input.id + '-listbox'; list.setAttribute('role', 'listbox'); list.hidden = true;
    wrap.appendChild(list);

    input.setAttribute('role', 'combobox');
    input.setAttribute('aria-autocomplete', 'list');
    input.setAttribute('aria-expanded', 'false');
    input.setAttribute('aria-controls', list.id);

    var shown = [], active = -1;

    function matches(q) {
      var t = q.toLowerCase().split(/\s+/).filter(Boolean), c = norm(q);
      if (!t.length) return items.slice();
      var hit = items.filter(function (it) {
        var low = it.toLowerCase();
        return t.every(function (w) { return low.indexOf(w) !== -1; }) || norm(it).indexOf(c) !== -1;
      });
      hit.sort(function (a, b) {                          // names that start with the text come first
        var sa = norm(a).indexOf(c) === 0 ? 0 : 1, sb = norm(b).indexOf(c) === 0 ? 0 : 1;
        return sa - sb;
      });
      return hit;
    }

    function esc(s) { return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); }

    function label(it, q) {
      var i = q ? it.toLowerCase().indexOf(q.toLowerCase()) : -1;
      if (i < 0) return esc(it);
      return esc(it.slice(0, i)) + '<b>' + esc(it.slice(i, i + q.length)) + '</b>' + esc(it.slice(i + q.length));
    }

    function render() {
      var q = input.value.trim();
      shown = matches(q).slice(0, MAX);
      active = -1;
      list.innerHTML = '';
      if (!shown.length) {
        var none = document.createElement('li');
        none.className = 'combo-empty'; none.setAttribute('aria-disabled', 'true');
        none.textContent = 'No match in the list. You can still type your own.';
        list.appendChild(none);
      }
      shown.forEach(function (it, i) {
        var li = document.createElement('li');
        li.id = list.id + '-' + i; li.setAttribute('role', 'option'); li.innerHTML = label(it, q);
        if (it.toLowerCase() === q.toLowerCase()) li.className = 'combo-current';
        li.addEventListener('mousedown', function (e) { e.preventDefault(); pick(i); });
        li.addEventListener('mousemove', function () { setActive(i, false); });
        list.appendChild(li);
      });
    }

    function setActive(i, scroll) {
      var opts = list.querySelectorAll('[role=option]');
      if (active >= 0 && opts[active]) { opts[active].classList.remove('combo-on'); opts[active].removeAttribute('aria-selected'); }
      active = i;
      if (i >= 0 && opts[i]) {
        opts[i].classList.add('combo-on'); opts[i].setAttribute('aria-selected', 'true');
        input.setAttribute('aria-activedescendant', opts[i].id);
        if (scroll) opts[i].scrollIntoView({ block: 'nearest' });
      } else input.removeAttribute('aria-activedescendant');
    }

    function open() { render(); list.hidden = false; input.setAttribute('aria-expanded', 'true'); }
    function close() { list.hidden = true; input.setAttribute('aria-expanded', 'false'); active = -1; input.removeAttribute('aria-activedescendant'); }

    function pick(i) {
      input.value = shown[i];
      close();
      input.dispatchEvent(new Event('input', { bubbles: true }));    // lets cpu-fields.js fill the family
      input.dispatchEvent(new Event('change', { bubbles: true }));
    }

    input.addEventListener('focus', open);
    input.addEventListener('click', function () { if (list.hidden) open(); });
    input.addEventListener('input', open);
    input.addEventListener('blur', close);
    btn.addEventListener('mousedown', function (e) {
      e.preventDefault();
      if (list.hidden) { input.focus(); open(); } else close();
    });
    input.addEventListener('keydown', function (e) {
      var n = shown.length;
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        if (list.hidden) open();
        if (n) setActive(active + 1 >= n ? 0 : active + 1, true);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        if (list.hidden) open();
        if (n) setActive(active <= 0 ? n - 1 : active - 1, true);
      } else if (e.key === 'Enter') {
        if (!list.hidden && active >= 0) { e.preventDefault(); pick(active); }
      } else if (e.key === 'Escape') {
        if (!list.hidden) { e.preventDefault(); close(); }
      } else if (e.key === 'Tab') close();
    });
  }

  Array.prototype.forEach.call(document.querySelectorAll('input[list]'), build);
})();
