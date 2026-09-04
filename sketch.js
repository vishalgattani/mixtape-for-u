// looping sine-ribbon background, adapted from a p5.js loop sketch
let ribbonColors;
const nFramesInLoop = 240;
const amplitude = 140;

function setup() {
  const c = createCanvas(windowWidth, windowHeight);
  c.parent('p5-bg');
  colorMode(RGB);
  ribbonColors = [
    color(255, 0, 0),
    color(0, 255, 0),
    color(0, 0, 255),
  ];
  noFill();
}

function windowResized() {
  resizeCanvas(windowWidth, windowHeight);
}

function draw() {
  const percent = (frameCount % nFramesInLoop) / nFramesInLoop;
  renderDesign(percent);
}

function renderDesign(percent) {
  blendMode(BLEND);
  background('#08060c');
  blendMode(SCREEN);

  noFill();
  strokeWeight(3);

  const v0 = 0.25;
  const v1 = 25;
  const v2 = 1;

  for (let i = 0; i < ribbonColors.length; i++) {
    stroke(ribbonColors[i]);
    beginShape();
    for (let sx = -20; sx <= width + 20; sx += 4) {
      const t = map(sx, 0, width, 0.0, v0);
      const sy = height / 2 + amplitude * sin((t * v1 + percent) * TWO_PI + (i * TWO_PI) / 3) * pow(abs(sin((t * v2 + percent) * TWO_PI)), 5);
      curveVertex(sx, sy);
    }
    endShape();
  }
}
