// Highlights the sidebar nav link matching whichever docs/main.html
// section is currently scrolled into view. Plain, static JS — no
// per-project data, so it needs no templating at all; read verbatim and
// inserted into a <script> tag by scaffold_service.py's _gen_main_html().
(function () {
  var sections = document.querySelectorAll('.k9x-doc-section[id]');
  var navLinks = document.querySelectorAll('.k9x-navlink');
  if (!sections.length || !('IntersectionObserver' in window)) return;
  var obs = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (entry.isIntersecting) {
        navLinks.forEach(function (l) {
          l.classList.toggle('active', l.getAttribute('href') === '#' + entry.target.id);
        });
      }
    });
  }, { rootMargin: '-15% 0px -70% 0px' });
  sections.forEach(function (s) { obs.observe(s); });
})();
