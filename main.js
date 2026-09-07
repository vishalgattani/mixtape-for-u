const cardEl = document.getElementById('card');
const titleEl = cardEl.querySelector('.card-title');
const artistEl = cardEl.querySelector('.card-artist');
const lyricBox = cardEl.querySelector('.lyric-box');
const lyricEl = cardEl.querySelector('.lyric');
const rewindBtn = document.getElementById('rewind-btn');
const playBtn = document.getElementById('play-btn');
const pauseBtn = document.getElementById('pause-btn');
const stopBtn = document.getElementById('stop-btn');
const forwardBtn = document.getElementById('forward-btn');

const LYRIC_MAX_SIZE = 30;
const LYRIC_MIN_SIZE = 13;

let lyrics = [];
let history = []; // indices into `lyrics`, in the order shown
let pointer = -1; // position within `history` currently displayed
let popped = false;
let busy = false;

fetch('lyrics.json')
  .then((r) => r.json())
  .then((list) => {
    lyrics = list;
    playBtn.disabled = lyrics.length === 0;
    updateNavButtons();
  })
  .catch(() => { playBtn.disabled = true; });

function updateNavButtons() {
  rewindBtn.disabled = pointer <= 0;
}

function pickNewIndex() {
  if (lyrics.length === 1) return 0;
  const last = history[history.length - 1];
  let i;
  do {
    i = Math.floor(Math.random() * lyrics.length);
  } while (i === last);
  return i;
}

// shrinks the lyric text down from LYRIC_MAX_SIZE until it fits lyric-box's
// fixed height — title/artist sizes are never touched.
function fitLyric() {
  let size = LYRIC_MAX_SIZE;
  lyricEl.style.fontSize = size + 'px';
  while (lyricEl.scrollHeight > lyricBox.clientHeight && size > LYRIC_MIN_SIZE) {
    size -= 1;
    lyricEl.style.fontSize = size + 'px';
  }
}

function render(index) {
  const entry = lyrics[index];
  titleEl.textContent = entry.title;
  artistEl.textContent = entry.artist;
  lyricEl.textContent = entry.lyric;
  cardEl.style.setProperty('--card-color', entry.color);

  requestAnimationFrame(() => {
    fitLyric();
    cardEl.classList.add('popped');
    popped = true;
    busy = false;
  });
}

// advance forward: redo into existing history if we've rewound, else pick a new lyric
function goForward() {
  if (pointer < history.length - 1) {
    pointer += 1;
  } else {
    history.push(pickNewIndex());
    pointer = history.length - 1;
  }
  updateNavButtons();
  render(history[pointer]);
}

function goBack() {
  if (pointer <= 0) return;
  pointer -= 1;
  updateNavButtons();
  render(history[pointer]);
}

function popThenRun(fn) {
  if (busy || lyrics.length === 0) return;
  busy = true;
  if (popped) {
    cardEl.classList.remove('popped');
    setTimeout(fn, 380);
  } else {
    fn();
  }
}

// play: resume the background animation; show the current (or first) card
playBtn.addEventListener('click', () => {
  if (typeof loop === 'function') loop();
  if (popped) return;
  popThenRun(() => {
    if (pointer === -1) {
      goForward();
    } else {
      render(history[pointer]);
    }
  });
});

// forward: skip to a new lyric (or redo one we'd rewound past)
forwardBtn.addEventListener('click', () => {
  if (typeof loop === 'function') loop();
  popThenRun(goForward);
});

// rewind: go back to the previously shown lyric, if any
rewindBtn.addEventListener('click', () => {
  if (pointer <= 0) return;
  if (typeof loop === 'function') loop();
  popThenRun(goBack);
});

// pause: freeze the background animation in place, leave the card as-is
pauseBtn.addEventListener('click', () => {
  if (typeof noLoop === 'function') noLoop();
});

// stop: retract the card and reset back to the idle animated background
stopBtn.addEventListener('click', () => {
  cardEl.classList.remove('popped');
  popped = false;
  if (typeof loop === 'function') loop();
});

window.addEventListener('resize', () => {
  if (popped) fitLyric();
});

if (document.fonts && document.fonts.ready) {
  document.fonts.ready.then(() => {
    if (popped) fitLyric();
  });
}
