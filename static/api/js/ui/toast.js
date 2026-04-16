/**
 * @description Displays a temporary toast message.
 * @param {string} msg - The message to display.
 */
const toast = msg => {
  const el = d.createElement('div');
  el.className = 'toast';
  el.textContent = msg;
  d.body.appendChild(el);
  setTimeout(() => el.remove(), 2500);
};

/**
 * @description Copies text to clipboard and provides visual feedback on a button.
 * @param {HTMLElement} btn - The button triggering the copy.
 * @param {string} text - The text to copy.
 * @param {number} [size=16] - Icon size for feedback.
 * @param {string} [msg] - Optional toast message.
 */
const copyWithFeedback = (btn, text, size = 16, msg) => {
  try {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
    } else {
      console.warn('Clipboard API not available');
    }
  } catch (err) {
    console.error('Failed to copy:', err);
  }
  
  if (msg) toast(msg);
  if (btn.dataset.copied === '1') return;
  const originalHtml = btn.innerHTML;
  btn.dataset.copied = '1';
  btn.innerHTML = ICON.check(size);
  setTimeout(() => {
    btn.innerHTML = originalHtml;
    delete btn.dataset.copied;
  }, 1500);
};
