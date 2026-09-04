const cardEl = document.getElementById('card');
const playBtn = document.getElementById('play-btn');
const pauseBtn = document.getElementById('pause-btn');
const stopBtn = document.getElementById('stop-btn');

let images = [];
let currentIndex = -1;
let popped = false;
let busy = false;

fetch('images/manifest.json')
  .then((r) => r.json())
  .then((list) => {
    images = list;
    playBtn.disabled = images.length === 0;
  })
  .catch(() => { playBtn.disabled = true; });

function pickNextIndex() {
  if (images.length === 1) return 0;
  let i;
  do {
    i = Math.floor(Math.random() * images.length);
  } while (i === currentIndex);
  return i;
}

function showNext() {
  currentIndex = pickNextIndex();
  cardEl.src = `images/${images[currentIndex]}`;
  cardEl.onload = () => {
    requestAnimationFrame(() => {
      cardEl.classList.add('popped');
      popped = true;
      busy = false;
    });
  };
}

// play: resume the background animation and show a new (random) lyric card
playBtn.addEventListener('click', () => {
  if (typeof loop === 'function') loop();
  if (busy || images.length === 0) return;
  busy = true;

  if (popped) {
    cardEl.classList.remove('popped');
    setTimeout(showNext, 380);
  } else {
    showNext();
  }
});

// pause: freeze the background animation in place, leave the card as-is
pauseBtn.addEventListener('click', () => {
  if (typeof noLoop === 'function') noLoop();
});

// stop: retract the card and reset back to the idle animated background
stopBtn.addEventListener('click', () => {
  cardEl.classList.remove('popped');
  popped = false;
  currentIndex = -1;
  if (typeof loop === 'function') loop();
});
