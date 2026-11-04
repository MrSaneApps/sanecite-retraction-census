/* Phase 2 charts: the charts are plain HTML from tools/charts.py and read without this
   script. It adds the Simple / Detailed switch, the share/count switch, year details on hover or tap, two-way legend highlight,
   copy buttons, and the share-image modes (#card, #square) used to render the PNGs. */
(function () {
  var h = location.hash;
  if (h === '#card' || h === '#square') document.documentElement.classList.add(h.slice(1));
  var fmt = function (n) { return Number(n).toLocaleString('en-US'); };
  var pct = function (k, n) { return (100 * k / n).toFixed(1) + '%'; };

  document.querySelectorAll('.vz').forEach(function (vz) {
    /* legend highlight for the 100 dots */
    vz.querySelectorAll('.vz-key li[data-k]').forEach(function (li) {
      li.tabIndex = 0;
      var on = function () { vz.setAttribute('data-hl', li.getAttribute('data-k')); };
      var off = function () { vz.removeAttribute('data-hl'); };
      li.addEventListener('mouseenter', on); li.addEventListener('focus', on);
      li.addEventListener('mouseleave', off); li.addEventListener('blur', off);
    });
    /* and the other way: a dot lights up its legend row */
    var dots = vz.querySelector('.dots');
    if (dots) {
      dots.addEventListener('mouseover', function (e) {
        var c = e.target.classList;
        if (c && c.contains('d') && c[1]) vz.setAttribute('data-hl', c[1]);
      });
      dots.addEventListener('mouseleave', function () { vz.removeAttribute('data-hl'); });
    }

    /* Simple / Detailed view */
    vz.querySelectorAll('.vz-view button').forEach(function (b) {
      b.addEventListener('click', function () {
        vz.setAttribute('data-view', b.getAttribute('data-view'));
        vz.querySelectorAll('.vz-view button').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
      });
    });

    /* years chart: share/count switch and per-year detail */
    var years = vz.querySelector('.years'), tip = vz.querySelector('.vz-tip');
    if (years) {
      vz.querySelectorAll('.vz-toggle:not(.vz-view) button').forEach(function (b) {
        b.addEventListener('click', function () {
          years.setAttribute('data-mode', b.getAttribute('data-mode'));
          vz.querySelectorAll('.vz-toggle:not(.vz-view) button').forEach(function (x) { x.setAttribute('aria-pressed', x === b ? 'true' : 'false'); });
        });
      });
      var show = function (yr) {
        var d = yr.dataset;
        tip.textContent = d.y + (d.y === '1' ? ' year' : ' years') + ' after retraction: ' + fmt(d.t) + ' citations · ' +
          pct(d.s, d.t) + ' cited it as support · ' + pct(d.p, d.t) + ' in passing · ' + pct(d.a, d.t) + ' flagged it';
      };
      years.querySelectorAll('.yr').forEach(function (yr) {
        yr.addEventListener('mouseenter', function () { show(yr); });
        yr.addEventListener('focus', function () { show(yr); });
        yr.addEventListener('click', function () { show(yr); });
      });
      if (tip) tip.textContent = 'Point at or tap a bar for that year.';
    }
  });

  /* copy caption / copy link; data-copy-li copies its fact line as shown (live numbers included) */
  document.querySelectorAll('[data-copy],[data-copy-li]').forEach(function (b) {
    b.addEventListener('click', function () {
      var li = b.hasAttribute('data-copy-li') && b.closest('li'), label = b.textContent;
      var text = li ? li.querySelector('span').innerText.replace(/\s*\n\s*/g, ' ') + ' Source: SaneCite, sanecite.com' : b.getAttribute('data-copy');
      var done = function () { b.textContent = 'Copied'; setTimeout(function () { b.textContent = label; }, 1600); };
      if (navigator.clipboard) navigator.clipboard.writeText(text).then(done, function () { window.prompt('Copy this:', text); });
      else window.prompt('Copy this:', text);
    });
  });
})();
