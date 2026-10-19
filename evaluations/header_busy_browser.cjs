const fs=require('fs');
const {chromium}=require('C:/Users/nagar/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const [url,out]=process.argv.slice(2);fs.mkdirSync(out,{recursive:true});
const overlap=(a,b)=>a&&b&&Math.min(a.x+a.width,b.x+b.width)>Math.max(a.x,b.x)&&Math.min(a.y+a.height,b.y+b.height)>Math.max(a.y,b.y);
(async()=>{const results=[];const quick=!!process.env.UI_HEADER_QUICK;let quickBrowser;
const cases=quick?[["chrome","C:/Program Files/Google/Chrome/Application/chrome.exe",320],["chrome","C:/Program Files/Google/Chrome/Application/chrome.exe",1440]]:[
 ['chrome','C:/Program Files/Google/Chrome/Application/chrome.exe',320],
 ['chrome','C:/Program Files/Google/Chrome/Application/chrome.exe',390],
 ['edge','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe',1440]];
for(const [engine,executablePath,width] of cases){
 const item={engine,width};let browser,page;
 try{
 browser=(quick&&quickBrowser)||await chromium.launch({executablePath,headless:true,timeout:20000});
 if(quick)quickBrowser=browser;
 page=await browser.newPage({viewport:{width,height:900}});
 await page.goto(url,{waitUntil:'domcontentloaded'});
 const prompt=page.getByRole('textbox',{name:'Message JeshlaAutoAI…',exact:true});
 await prompt.waitFor({timeout:120000});
 await page.waitForFunction(()=>document.querySelector('[data-testid="stApp"]')?.getAttribute('data-test-script-state')==='notRunning');
 const actions=page.locator('.st-key-chat_header_actions');
 const menu=page.locator('[data-testid="stMainMenu"] button, button[data-testid="stMainMenu"]').first();
 item.idleActions=await actions.boundingBox();item.menu=await menu.boundingBox();
 await prompt.fill('Header overlap test');await prompt.press('Enter');
 const stop=page.getByRole('button',{name:'Stop',exact:true});
 await stop.waitFor({timeout:15000});
 item.runningActions=await actions.boundingBox();item.stop=await stop.boundingBox();
 item.appRunState=await page.locator('[data-testid="stApp"]').getAttribute('data-test-script-state');
 item.overlapsStop=overlap(item.runningActions,item.stop);
 const status=page.locator('[data-testid="stStatusWidget"]');
 item.statusBox=await status.count()?await status.first().boundingBox():item.stop;
 item.overlapsStatus=overlap(item.runningActions,item.statusBox);
 item.overlapsMenu=overlap(item.runningActions,await menu.boundingBox());
 item.toolbar=[...await page.locator('[data-testid="stHeader"] [data-testid]').evaluateAll(es=>es.map(e=>({id:e.dataset.testid,text:e.textContent?.slice(0,80),box:{x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y,width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}})))];
 item.stopHitTest=await stop.evaluate(e=>{const b=e.getBoundingClientRect(),hit=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2);return e===hit||e.contains(hit);});
 item.actionsHitTest=await page.locator('.st-key-provider_information button:visible').first().evaluate(e=>{const b=e.getBoundingClientRect(),hit=document.elementFromPoint(b.x+b.width/2,b.y+b.height/2);return e===hit||e.contains(hit);});
 await page.screenshot({path:out+'/'+engine+'-'+width+'-running.png',fullPage:true});
 await page.getByText('Fixture answer from supplied evidence.',{exact:true}).last().waitFor({timeout:30000});
 await page.waitForFunction(()=>document.querySelector('[data-testid="stApp"]')?.getAttribute('data-test-script-state')==='notRunning');
 await page.locator('.st-key-chat_attachments button:visible').first().click();
 await page.getByText('No documents attached to this chat.',{exact:true}).waitFor();item.attachmentsOpen=true;
 await page.keyboard.press('Escape');
 await page.locator('.st-key-provider_information button:visible').first().click();
 await page.getByText('Configured model: fixture-groq',{exact:true}).waitFor();item.infoOpens=true;
 await page.keyboard.press('Escape');await menu.click();
 const rerun=page.locator('[data-testid="stMainMenuItem-rerun"]');
 const auto=page.locator('[data-testid="stMainMenuItem-autoRerun"]');
 await rerun.waitFor();await auto.waitFor();
 await page.screenshot({path:out+'/'+engine+'-'+width+'-menu.png',fullPage:true});item.menuOpens=true;item.rerunInMenu=true;item.autoRerunInMenu=true;
 if(engine==='chrome'&&width===320){
  const renders=()=>page.locator('[data-fixture-renders]').last().getAttribute('data-fixture-renders').then(Number);
  let count=await renders();
  await page.keyboard.press('Escape');
  fs.appendFileSync(process.env.UI_FIXTURE_ENTRY,'\n# Manual rerun acceptance marker\n');
  await page.getByText('File change.',{exact:true}).waitFor({state:'attached',timeout:20000});
  item.fileChangePromptHidden=!(await page.getByText('File change.',{exact:true}).isVisible());
  await menu.click();await page.locator('[data-testid="stMainMenuItem-rerun"]').click();
  await page.waitForFunction(old=>Number(document.querySelector('[data-fixture-renders]')?.dataset.fixtureRenders)>old,count,{timeout:20000});item.manualRerunWorks=true;
  count=await renders();await menu.click();
  await page.locator('[data-testid="stMainMenuItem-autoRerun"]').click();
  await page.keyboard.press('Escape');
  await page.locator('[data-testid="stMainMenuItem-autoRerun"]').waitFor({state:'hidden'});
  await menu.click();
  item.autoRerunEnabled=(await page.locator('[data-testid="stMainMenuItem-autoRerun"]').getAttribute('aria-checked'))==='true';
  await page.keyboard.press('Escape');
  fs.appendFileSync(process.env.UI_FIXTURE_ENTRY,'\n# Automatic rerun acceptance marker\n');
  await page.waitForFunction(old=>Number(document.querySelector('[data-fixture-renders]')?.dataset.fixtureRenders)>old,count,{timeout:20000});item.autoRerunWorks=true;
  await menu.click();await page.locator('[data-testid="stMainMenuItem-autoRerun"]').click();
 }else{await page.keyboard.press('Escape');}

 item.pageOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth+2);
 item.status=!item.overlapsStop&&!item.overlapsStatus&&!item.overlapsMenu&&item.stopHitTest&&item.actionsHitTest&&item.attachmentsOpen&&item.infoOpens&&item.menuOpens&&item.rerunInMenu&&item.autoRerunInMenu&&(width!==320||(item.fileChangePromptHidden&&item.manualRerunWorks&&item.autoRerunEnabled&&item.autoRerunWorks))&&!item.pageOverflow?'passed':'failed';
 }catch(e){item.status='failed';item.error=String(e.message).slice(0,600);if(page){item.fixtureVisibleText=(await page.locator('body').innerText().catch(()=>'' )).slice(0,1200);await page.screenshot({path:out+'/'+engine+'-'+width+'-error.png',fullPage:true}).catch(()=>{});}}
 finally{if(page)await page.close().catch(()=>{});if(browser&&!quick)await browser.close();}
 results.push(item);console.log(JSON.stringify(item));
}
if(quickBrowser)await quickBrowser.close();
fs.writeFileSync(out+'/results.json',JSON.stringify({scope:'Synthetic slow-response fixture; installed Chrome/Edge, emulated widths',results},null,2));
if(results.some(r=>r.status!=='passed'))process.exitCode=1;
})().catch(e=>{console.error(e.message);process.exit(1)});
