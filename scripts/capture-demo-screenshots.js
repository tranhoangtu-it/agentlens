/**
 * Capture demo screenshots of AgentLens dashboard for README.
 * Run: node scripts/capture-demo-screenshots.js
 * Requires: server on :8000 with demo data, dashboard on :5173
 */

const puppeteer = require('puppeteer');
const path = require('path');

const OUT_DIR = path.join(__dirname, 'screenshots');
const DASHBOARD_URL = 'http://localhost:5173';

async function sleep(ms) {
  return new Promise(r => setTimeout(r, ms));
}

async function main() {
  const browser = await puppeteer.launch({
    headless: true,
    defaultViewport: { width: 1440, height: 900 },
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  });

  const page = await browser.newPage();

  // 1. Trace list page
  console.log('1/3 Capturing trace list...');
  await page.goto(DASHBOARD_URL, { waitUntil: 'domcontentloaded', timeout: 15000 });
  await sleep(3000);
  await page.screenshot({ path: path.join(OUT_DIR, '01-trace-list.png'), fullPage: false });
  console.log('  ✓ 01-trace-list.png');

  // 2. Click CodingAgent trace (row index 2 — sorted newest first: Monitoring, Data, Coding, Research)
  console.log('2/3 Capturing CodingAgent topology graph...');
  const traceRows = await page.$$('table tbody tr');
  // Find the CodingAgent row
  let codingRowIdx = -1;
  for (let i = 0; i < traceRows.length; i++) {
    const text = await traceRows[i].evaluate(el => el.textContent);
    if (text.includes('CodingAgent')) { codingRowIdx = i; break; }
  }
  if (codingRowIdx >= 0) {
    await traceRows[codingRowIdx].click();
    await sleep(3000);
    await page.screenshot({ path: path.join(OUT_DIR, '02-trace-detail.png'), fullPage: false });
    console.log('  ✓ 02-trace-detail.png');
  } else {
    console.log('  ⚠ CodingAgent not found, trying first row');
    if (traceRows.length > 0) {
      await traceRows[0].click();
      await sleep(3000);
      await page.screenshot({ path: path.join(OUT_DIR, '02-trace-detail.png'), fullPage: false });
      console.log('  ✓ 02-trace-detail.png (fallback)');
    }
  }

  // 3. Click on a node to show span detail panel
  console.log('3/3 Capturing span detail panel...');
  const nodes = await page.$$('.react-flow__node');
  if (nodes.length > 1) {
    // Click the second node (a child span — tool_call or llm_call)
    await nodes[1].click();
    await sleep(1500);
    await page.screenshot({ path: path.join(OUT_DIR, '03-span-detail.png'), fullPage: false });
    console.log('  ✓ 03-span-detail.png');
  } else if (nodes.length > 0) {
    await nodes[0].click();
    await sleep(1500);
    await page.screenshot({ path: path.join(OUT_DIR, '03-span-detail.png'), fullPage: false });
    console.log('  ✓ 03-span-detail.png');
  } else {
    console.log('  ⚠ No graph nodes found');
  }

  await browser.close();
  console.log(`\nDone! Screenshots saved to ${OUT_DIR}/`);
}

main().catch(err => {
  console.error('Error:', err.message);
  process.exit(1);
});
