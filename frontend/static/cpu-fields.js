// Add / Edit form: fills "CPU family" from the CPU (asks /api/cpu-family) and warns when the two do not match.
// The server checks the pair again on Save, so this script only helps; it never decides.
(function () {
  var cpu = document.getElementById('f-cpu'), fam = document.getElementById('f-cpu_family');
  var hint = document.getElementById('cpu-hint');
  if (!cpu || !fam || !hint) return;
  var url = cpu.getAttribute('data-url'), timer = null, autoFilled = false, expected = null, known = false;

  function key(s) { return (s || '').replace(/\s+/g, '').toLowerCase(); }

  function show() {
    var f = fam.value.trim();
    hint.style.color = '';
    if (!cpu.value.trim()) { hint.textContent = ''; return; }
    if (!known) {
      hint.textContent = 'This CPU is not recognised, so its family cannot be checked. Use the family "Other" or pick a CPU from the list.';
      hint.style.color = f && key(f) !== 'other' ? 'var(--danger, #c0392b)' : '';
    } else if (f && key(f) !== key(expected)) {
      hint.textContent = 'This CPU belongs to the family "' + expected + '", not "' + f + '".';
      hint.style.color = 'var(--danger, #c0392b)';
    } else {
      hint.textContent = 'CPU family: ' + expected + '.';
    }
  }

  function ask() {
    var value = cpu.value.trim();
    if (!value) { expected = null; known = false; show(); return; }
    fetch(url + '?cpu=' + encodeURIComponent(value))
      .then(function (r) { return r.json(); })
      .then(function (d) {
        if (cpu.value.trim() !== value) return;          // the box changed while waiting
        known = !!d.family; expected = d.family;
        if (known && (fam.value.trim() === '' || autoFilled)) { fam.value = d.family; autoFilled = true; }
        if (!known && (fam.value.trim() === '' || autoFilled)) { fam.value = d.other; autoFilled = true; }
        show();
      })
      .catch(function () { hint.textContent = ''; });
  }

  cpu.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(ask, 250); });
  cpu.addEventListener('change', ask);
  fam.addEventListener('input', function () { autoFilled = false; show(); });
  ask();                                                 // checks the values already in the form (Edit page)
})();
