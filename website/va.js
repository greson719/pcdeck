(function () {
  try {
    var params = new URLSearchParams(window.location.search);
    if (params.get('notrack') === '1' || params.get('admin') === '1') {
      localStorage.setItem('pcdeck_no_track', '1');
      alert('PCDeck: Analytics tracking disabled on this device.');
    } else if (params.get('track') === '1') {
      localStorage.removeItem('pcdeck_no_track');
      alert('PCDeck: Analytics tracking re-enabled on this device.');
    }
  } catch (e) {}

  if (localStorage.getItem('pcdeck_no_track') !== '1') {
    var s = document.createElement('script');
    s.defer = true;
    s.src = '/_vercel/insights/script.js';
    document.head.appendChild(s);
  }
})();
