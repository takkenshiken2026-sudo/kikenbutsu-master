(function () {
  var btn = document.getElementById('site-scroll-top');
  if (!btn) return;
  btn.addEventListener('click', function () {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  });
  var threshold = 400;
  function onScroll() {
    btn.classList.toggle('is-visible', window.scrollY > threshold);
  }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();
})();
