// Renders scenes.html frame by frame and pipes the frames into ffmpeg.
// Usage: node render.js [output.mp4]
const { chromium } = require('playwright');
const { spawn, execFileSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const FPS = 30;
const out = process.argv[2] || path.join(__dirname, 'what-is-a-prompt.mp4');

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1280, height: 720 }, deviceScaleFactor: 1.5 });
  await page.goto('file://' + path.join(__dirname, 'scenes.html'));
  await page.evaluate(() => document.fonts.ready);
  const duration = await page.evaluate(() => window.DURATION);

  // Sidecar subtitles (they are also burned into the video by scenes.html)
  const cues = await page.evaluate(() => window.CUES);
  const ts = sec => {
    const ms = Math.round(sec * 1000), p = (n, w = 2) => String(n).padStart(w, '0');
    return `${p(Math.floor(ms / 3600000))}:${p(Math.floor(ms / 60000) % 60)}:${p(Math.floor(ms / 1000) % 60)},${p(ms % 1000, 3)}`;
  };
  const srt = out.replace(/\.mp4$/, '') + '.he.srt';
  fs.writeFileSync(srt, cues.map(([s, e, text], i) => `${i + 1}\n${ts(s)} --> ${ts(e)}\n${text}\n`).join('\n'));

  execFileSync('python3', ['music.py', String(duration)], { cwd: __dirname });
  const music = path.join(__dirname, 'music.wav');

  const ffmpeg = spawn('ffmpeg', [
    '-y', '-f', 'image2pipe', '-framerate', String(FPS), '-c:v', 'mjpeg', '-i', '-',
    '-i', music, '-map', '0:v', '-map', '1:a',
    '-c:a', 'aac', '-b:a', '160k',
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-preset', 'medium',
    '-movflags', '+faststart', out,
  ], { stdio: ['pipe', 'inherit', 'inherit'] });

  const frames = Math.round(duration * FPS);
  for (let i = 0; i < frames; i++) {
    await page.evaluate(t => window.render(t), i / FPS);
    const buf = await page.screenshot({ type: 'jpeg', quality: 92 });
    if (!ffmpeg.stdin.write(buf)) await new Promise(r => ffmpeg.stdin.once('drain', r));
    if (i % 150 === 0) console.log(`frame ${i}/${frames}`);
  }
  ffmpeg.stdin.end();
  await new Promise(r => ffmpeg.on('close', r));
  await browser.close();
  console.log('wrote', out);
})();
