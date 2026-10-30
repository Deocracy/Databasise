// Shared helpers for every screen. Text only ever reaches the DOM through textContent (Pitfall 11).
function h(tag, text, cls) {
  var node = document.createElement(tag);
  if (text !== undefined && text !== null) node.textContent = text;
  if (cls) node.className = cls;
  return node;
}

function clearNode(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function copyText(text, flash) {
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(function () {}, function () {}).catch(function () {});
    }
  } catch (e) {
    // clipboard access is optional in a file:// mockup
  }
  if (flash) {
    flash.hidden = false;
    setTimeout(function () {
      flash.hidden = true;
    }, 1500);
  }
}
