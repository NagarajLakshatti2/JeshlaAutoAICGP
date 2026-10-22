/* Actual Chrome/UI interaction; data is supplied only by the temporary fixture. */
const fs = require('fs');
const {chromium} = require('C:/Users/nagar/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const [url, out, phase, casesPath] = process.argv.slice(2);
const cases = JSON.parse(fs.readFileSync(casesPath, 'utf8'));
const report = {status: 'failed', phase, engine: 'chrome', width: 1440, submitted: {alpha: 0, beta: 0}, checks: []};
let browser;
const watchdog = setTimeout(async () => { if (browser) await browser.close().catch(() => {}); }, 210000);
async function settled(page) {
  await page.waitForFunction(() => document.querySelector('[data-testid="stApp"]')?.getAttribute('data-test-script-state') === 'notRunning', {}, {timeout: 60000});
}
async function openChat(page, name) {
  await page.locator('.st-key-open_chat_' + name + ' button:visible').click();
  await page.getByText(cases[name].turns[0][0], {exact: true}).waitFor({timeout: 30000});
  await settled(page);
}
async function send(page, name, question) {
  const before = await page.getByTestId('stChatMessage').count();
  const prompt = page.getByRole('textbox', {name: 'Message JeshlaAutoAI…', exact: true});
  await prompt.fill(question);
  await prompt.press('Enter');
  await page.waitForFunction(count => document.querySelectorAll('[data-testid="stChatMessage"]').length === count + 2, before, {timeout: 90000});
  await settled(page);
  report.submitted[name] += 1;
}
async function probe(page, name, label) {
  await send(page, name, 'REOPEN_CHECK ' + cases[name].marker);
  const answer = (await page.getByTestId('stChatMessage').last().getByTestId('stMarkdownContainer').innerText()).trim();
  const passed = answer === cases[name].marker;
  report.checks.push({label, restoredSummaryUsed: passed});
  if (!passed) throw new Error('Persisted summary probe did not match its chat.');
}
(async () => {
  let page;
  try {
    browser = await chromium.launch({executablePath: 'C:/Program Files/Google/Chrome/Application/chrome.exe', headless: true, timeout: 30000});
    page = await browser.newPage({viewport: {width: 1440, height: 900}});
    await page.goto(url, {waitUntil: 'domcontentloaded', timeout: 30000});
    await page.getByRole('textbox', {name: 'Message JeshlaAutoAI…', exact: true}).waitFor({timeout: 120000});
    await settled(page);
    if (phase === 'create') {
      for (const name of ['alpha', 'beta']) {
        await openChat(page, name);
        await send(page, name, 'Please acknowledge my summary check.');
        await page.getByText('Older conversation summarized. Full turns remain in the transcript archive.', {exact: true}).waitFor({timeout: 10000});
        report.checks.push({label: name + ' summary notice', summaryCreated: true});
        await probe(page, name, name + ' before reload');
      }
      await page.reload({waitUntil: 'domcontentloaded'});
      await page.getByRole('textbox', {name: 'Message JeshlaAutoAI…', exact: true}).waitFor({timeout: 60000});
      await settled(page);
      await openChat(page, 'alpha');
      await probe(page, 'alpha', 'alpha after page reload');
    } else {
      for (const name of ['alpha', 'beta', 'alpha']) {
        await openChat(page, name);
        await probe(page, name, name + ' after server/browser restart');
      }
    }
    await page.screenshot({path: out + '/' + phase + '.png', fullPage: true});
    report.status = 'passed';
  } catch (error) {
    report.error = String(error.message).slice(0, 1200);
    if (page) await page.screenshot({path: out + '/' + phase + '-failed.png', fullPage: true}).catch(() => {});
  } finally {
    clearTimeout(watchdog);
    if (browser) await browser.close().catch(() => {});
    fs.writeFileSync(out + '/' + phase + '.json', JSON.stringify(report, null, 2));
    process.exitCode = report.status === 'passed' ? 0 : 1;
  }
})();
