/**
 * render-topic.mjs
 * Reads research/topics/{slug}.json, extracts the best hook/stat/insight,
 * renders the Remotion InsightVideo, and saves to assets/videos/{slug}.mp4
 *
 * Uses a two-step approach (workaround for macOS 12 AVFoundation limitation):
 *   1. Remotion renders PNG/JPEG frame sequence
 *   2. ffmpeg-static stitches frames into MP4
 *
 * Usage:
 *   node scripts/render-topic.mjs <slug>
 *   node scripts/render-topic.mjs ai-agents-enterprise
 */

import { execSync } from "child_process";
import { readFileSync, writeFileSync, mkdirSync, existsSync, rmSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { tmpdir } from "os";
import { createRequire } from "module";

const require = createRequire(import.meta.url);
const __dir = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(__dir, "../..");
// ffmpeg-static exports the binary path directly (not the JS entry)
const FFMPEG = require("ffmpeg-static");

const slug = process.argv[2];
if (!slug) {
  console.error("Usage: node scripts/render-topic.mjs <slug>");
  process.exit(1);
}

// ── Load research JSON ──────────────────────────────────────────────────────
const jsonPath = resolve(ROOT, `research/topics/${slug}.json`);
if (!existsSync(jsonPath)) {
  console.error(`Not found: ${jsonPath}`);
  process.exit(1);
}

const data = JSON.parse(readFileSync(jsonPath, "utf-8"));

// ── Extract props from insights ─────────────────────────────────────────────
function extractHooks(insights) {
  const hooks = [];
  const hookRegex = /HOOK:\s*\*\*(.+?)\*\*\nCORE INSIGHT:\s*(.+?)(?:\n|$)/gms;
  let m;
  while ((m = hookRegex.exec(insights)) !== null) {
    hooks.push({ hook: m[1].trim(), insight: m[2].trim() });
  }
  return hooks;
}

function extractTopStat(insights) {
  const match = insights.match(/\*\*([^*]+?):\*\*\s*([^\n*]+)/);
  return match ? `${match[1]}: ${match[2].trim()}` : null;
}

function extractContrarian(insights) {
  const match = insights.match(/## 2\. THE THING EXPERTS GET WRONG\n([\s\S]+?)(?=\n## )/);
  if (!match) return null;
  const sentence = match[1].replace(/\*\*/g, "").replace(/\[.*?\]/g, "").trim().split(/\.\s+/)[0];
  return sentence ? sentence + "." : null;
}

const hooks = extractHooks(data.insights || "");
const topStat = extractTopStat(data.insights || "");
const contrarian = extractContrarian(data.insights || "");

const props = {
  topic: data.topic,
  stat: topStat || "The data will surprise you.",
  insight: hooks[0]?.insight || "AI is changing how top firms operate — faster than most expect.",
  contrarian: contrarian || "The technology isn't the problem. The process is.",
  cta: "Drop a comment → I'll DM you the full playbook",
};

// ── Render ───────────────────────────────────────────────────────────────────
const outDir = resolve(ROOT, "assets/videos");
mkdirSync(outDir, { recursive: true });
const outFile = resolve(outDir, `${slug}.mp4`);
const seqDir = resolve(tmpdir(), `remotion-seq-${slug}`);
mkdirSync(seqDir, { recursive: true });

// Write props to temp file
const tmpProps = resolve(tmpdir(), `remotion-props-${slug}.json`);
writeFileSync(tmpProps, JSON.stringify(props), "utf-8");

console.log(`\nRendering: ${data.topic}`);
console.log(`Stat:      ${props.stat.slice(0, 80)}`);
console.log(`Output:    ${outFile}\n`);

const remotionDir = resolve(__dir, "..");

try {
  // Step 1: Render frame sequence
  console.log("Step 1/2: Rendering frames...");
  execSync(
    `npx remotion render src/index.ts InsightVideo "${seqDir}" --sequence --muted --props="${tmpProps}"`,
    { cwd: remotionDir, stdio: "inherit" }
  );

  // Step 2: Stitch with ffmpeg-static (macOS 12 compatible)
  console.log("\nStep 2/2: Stitching video...");
  execSync(
    `"${FFMPEG}" -y -framerate 30 -i "${seqDir}/element-%03d.jpeg" -c:v libx264 -pix_fmt yuv420p -crf 18 "${outFile}"`,
    { stdio: "inherit" }
  );

  console.log(`\nDone → ${outFile}`);
  console.log(`\nGitHub raw URL (after push):`);
  console.log(`https://raw.githubusercontent.com/Rns-lab/social-media/main/assets/videos/${slug}.mp4`);
} finally {
  // Cleanup temp files
  try { rmSync(tmpProps); } catch {}
  try { rmSync(seqDir, { recursive: true }); } catch {}
}
