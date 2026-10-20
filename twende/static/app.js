// Swap the "Panda from" and "Shuka at" boxes on the home page.
const swapButton = document.getElementById('swap');
if (swapButton) {
  swapButton.addEventListener('click', () => {
    const from = document.getElementById('origin');
    const to = document.getElementById('destination');
    [from.value, to.value] = [to.value, from.value];
  });
}
