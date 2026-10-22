const fs = require('fs');
const { chromium } = require('C:/Users/nagar/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const [url, out] = process.argv.slice(2);
async function settled(page) {
  await page.waitForFunction(() => document.querySelector('[data-testid="stApp"]')?.getAttribute('data-test-script-state') === 'notRunning', {}, {timeout: 30000});
}
(async () => {
  const results = [];
  for (const [engine, executablePath] of [['chrome', 'C:/Program Files/Google/Chrome/Application/chrome.exe'], ['edge', 'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe']]) {
    const browser = await chromium.launch({executablePath, headless: true, timeout: 20000});
    try {
      for (const width of [360, 1440]) {
        const page = await browser.newPage({viewport: {width, height: 900}});
        const item = {engine, width};
        try {
          await page.goto(url, {waitUntil: 'domcontentloaded', timeout: 30000});
          const composer = page.locator('.st-key-message_composer');
          await composer.waitFor({timeout: 30000});await settled(page);
          // Observe while the reply is deliberately delayed, as well as settled DOM.
          await page.evaluate(() => {
            window.composerSamples = [];
            const sample = () => {
              const boxes = [...document.querySelectorAll('.st-key-message_composer')].filter(e => e.getBoundingClientRect().width > 0);
              const count = boxes.length;
              if (count || window.composerSamples.length) window.composerSamples.push(count);
            };
            window.composerObserver = new MutationObserver(sample);
            window.composerObserver.observe(document.body, {subtree: true, childList: true});sample();
          });
          for (const text of ['hi', 'how are you']) {
            const input = page.locator('.st-key-message_composer textarea');
            await input.fill(text);await input.press('Enter');
            await page.waitForFunction(n => document.querySelectorAll('[data-testid="stChatMessage"]').length === n, text === 'hi' ? 2 : 4, {timeout: 20000});
            await settled(page);
          }
          item.maxComposersDuringRerun = await page.evaluate(() => Math.max(...window.composerSamples));
          item.finalComposers = await composer.count();
          item.chatInputs = await page.locator('[data-testid="stChatInput"]').count();
          item.messages = await page.locator('[data-testid="stChatMessage"]').count();
          item.composerAfterMessages = await page.evaluate(() => {
            const composer = document.querySelector('.st-key-message_composer');
            const messages = [...document.querySelectorAll('[data-testid="stChatMessage"]')];
            return messages.every(message => (message.compareDocumentPosition(composer) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0);
          });
          item.horizontalOverflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth + 2);
          await page.screenshot({path: `${out}/${engine}-${width}.png`, fullPage: true});
          await page.reload();await page.locator('.st-key-message_composer').waitFor();await settled(page);
          item.refreshComposers = await page.locator('.st-key-message_composer').count();
          item.status = item.maxComposersDuringRerun === 1 && item.finalComposers === 1 && item.chatInputs === 1 && item.messages === 4 && item.composerAfterMessages && !item.horizontalOverflow && item.refreshComposers === 1 ? 'passed' : 'failed';
        } catch (error) {
          item.status = 'failed';item.error = String(error.message).slice(0, 500);
          await page.screenshot({path: `${out}/${engine}-${width}-error.png`, fullPage: true}).catch(() => {});
        }
        results.push(item);await page.close();
      }
    } finally { await browser.close(); }
  }
  fs.writeFileSync(`${out}/results.json`, JSON.stringify({scope: 'Isolated fake responses; actual headless Chrome/Edge, emulated mobile/desktop sizes, no provider calls', results}, null, 2));
  console.log(JSON.stringify(results));
  if (results.some(row => row.status !== 'passed')) process.exitCode = 1;
})().catch(error => {console.error(error.message);process.exitCode = 1;});
