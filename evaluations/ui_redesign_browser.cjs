const fs=require('fs');
const {chromium}=require('C:/Users/nagar/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const [url,out]=process.argv.slice(2);fs.mkdirSync(out,{recursive:true});
async function settled(page){await page.waitForFunction(()=>document.querySelector('[data-testid="stApp"]')?.getAttribute('data-test-script-state')==='notRunning',{},{timeout:30000});}
(async()=>{const results=[];
for(const [engine,executablePath] of [['chrome','C:/Program Files/Google/Chrome/Application/chrome.exe'],['edge','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe']]){
 let browser;
 try{browser=await chromium.launch({executablePath,headless:true,timeout:20000});
 for(const width of (process.env.UI_REDESIGN_FULL?[360,390,768,1440]:[engine==='chrome'?360:1440])){
 const page=await browser.newPage({viewport:{width,height:900}});const item={engine,width};
 try{
 await page.goto(url,{waitUntil:'domcontentloaded',timeout:30000});
 await page.getByRole('heading',{name:'What would you like to build?',exact:true}).waitFor({timeout:30000});
 await page.locator('.st-key-browser_provider [role="combobox"]').waitFor();await settled(page);
 item.landingClean=await page.getByText('Existing saved answer',{exact:true}).count()===0;
 item.providerOnly=!(await page.locator('.st-key-browser_provider').innerText()).includes('fixture-');
 item.initialOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+2);
 const headerActions=page.locator('.st-key-chat_header_actions');
 await headerActions.waitFor();
 item.headerActionsInTopBar=await headerActions.evaluate(e=>{const box=e.getBoundingClientRect();return box.top>=0&&box.top<20&&box.right<=window.innerWidth-32;});
 item.nativeOptionsMenuVisible=await page.locator('[data-testid="stMainMenu"] button, button[data-testid="stMainMenu"]').first().isVisible();
 item.developerPromptsHidden=!(await page.getByText('File change.',{exact:true}).first().isVisible())&&!(await page.getByText('Always rerun',{exact:true}).first().isVisible())&&!(await page.getByText('Deploy',{exact:true}).first().isVisible());
 fs.writeFileSync(out+'/'+engine+'-'+width+'-header.json',JSON.stringify(await page.evaluate(()=>({header:[...document.querySelectorAll('[data-testid="stHeader"], [data-testid="stSidebar"], .st-key-chat_header_actions')].map(e=>({key:e.dataset.testid||e.className,zIndex:getComputedStyle(e).zIndex,box:{x:e.getBoundingClientRect().x,y:e.getBoundingClientRect().y,width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}}))})),null,2));

 await page.screenshot({path:out+'/'+engine+'-'+width+'-landing.png',fullPage:true});
 await page.locator('.st-key-add_to_chat button:visible').first().click();
 await page.getByText('Upload documents',{exact:true}).click();
 await page.locator('input[type=file]').setInputFiles([{name:'requirements.txt',mimeType:'text/plain',buffer:Buffer.from('UI redesign fixture requirement')},{name:'design-notes.md',mimeType:'text/markdown',buffer:Buffer.from('Two files in this chat only.')}]);
 await page.getByText('design-notes.md',{exact:true}).waitFor();await settled(page);
 await page.getByRole('button',{name:'Attach to chat',exact:true}).click();
 await page.waitForFunction(()=>document.querySelector('.st-key-chat_attachments')?.textContent.includes('2'),{},{timeout:30000});
 await settled(page);
 await page.keyboard.press('Escape');
 await page.locator('.st-key-chat_attachments button:visible').first().click();
 await page.getByText('requirements.txt',{exact:true}).waitFor();
 item.attachmentsListOnly=await page.getByRole('textbox',{name:'Document preview',exact:true}).count()===0;
 await page.getByText('requirements.txt',{exact:true}).click();
 const preview=page.getByRole('textbox',{name:'Document preview',exact:true}).first();await preview.waitFor();item.preview=await preview.inputValue()==='UI redesign fixture requirement';
 await page.getByRole('button',{name:'Remove attachment',exact:true}).first().click();
 await page.waitForFunction(()=>document.querySelector('.st-key-chat_attachments')?.textContent.includes('1'),{},{timeout:30000});
 await settled(page);
 await page.keyboard.press('Escape');
 await page.locator('.st-key-chat_attachments button:visible').first().click();
 await page.getByText('design-notes.md',{exact:true}).click();
 const remainingPreview=page.getByRole('textbox',{name:'Document preview',exact:true}).first();
 await remainingPreview.waitFor();item.removalKeepsCorrectPreview=await remainingPreview.inputValue()==='Two files in this chat only.';

 await page.keyboard.press('Escape');
 const prompt=page.getByRole('textbox',{name:'Message JeshlaAutoAI…',exact:true});
 await prompt.fill('Summarize my attachments');await prompt.press('Enter');
 await page.getByText('Fixture answer from supplied evidence.',{exact:true}).last().waitFor({timeout:20000});item.chatWorks=true;
 item.firstMessageStartsNewChat=await page.getByText('Existing saved answer',{exact:true}).count()===0;
 const opener=page.locator('[data-testid="stSidebarCollapsedControl"] button, [data-testid="stExpandSidebarButton"], [data-testid="collapsedControl"] button').first();
 if(await opener.isVisible())await opener.click();
 await page.locator('.st-key-open_memory button:visible').click();
 await page.getByRole('button',{name:'Show saved facts',exact:true}).click();
 const reference=page.getByRole('textbox',{name:'long_reference',exact:true});await reference.waitFor();
 item.memoryWraps=await reference.evaluate(e=>e.scrollWidth<=e.clientWidth+2);
 await page.keyboard.press('Escape');await page.getByRole('dialog').waitFor({state:'hidden'});
 await page.locator('.st-key-open_settings button:visible').click();await page.getByRole('dialog').waitFor();
 await page.getByRole('dialog').getByRole('combobox',{name:'Provider for next restart',exact:true}).waitFor();
 item.settingsDropdown=await page.getByRole('dialog').getByRole('combobox',{name:'Provider for next restart',exact:true}).count()===1&&await page.getByRole('dialog').getByRole('radio').count()===0;
 await page.keyboard.press('Escape');await page.getByRole('dialog').waitFor({state:'hidden'});
 await page.locator('.st-key-open_chat_default button:visible').click();
 await page.getByText('Existing saved answer',{exact:true}).waitFor();item.generalOnlyOnSelection=true;
 await page.locator('.st-key-create_new_chat button:visible').click();
 await page.getByRole('heading',{name:'What would you like to build?',exact:true}).waitFor();
 item.newChatClean=!/\b[1-5]\b/.test(await page.locator('.st-key-chat_attachments').innerText());
 const closeSidebar=page.locator('[data-testid="stSidebar"] button:visible').filter({hasText:'keyboard_double_arrow_left'}).first();
 if(width<1000&&await closeSidebar.isVisible())await closeSidebar.click();
 const longMessage='x'.repeat(120),longTitle=longMessage.slice(0,100);
 await prompt.fill(longMessage);await prompt.press('Enter');
 await page.getByText('Fixture answer from supplied evidence.',{exact:true}).last().waitFor({timeout:30000});await settled(page);
 if(await opener.isVisible())await opener.click();
 await page.getByRole('button',{name:longTitle,exact:true}).first().waitFor();item.longTitleSaved=true;
 await page.locator('[data-testid="stSidebar"]').evaluate(async e=>{await Promise.all(e.getAnimations({subtree:true}).filter(a=>Number.isFinite(a.effect.getTiming().iterations)).map(a=>a.finished.catch(()=>{})));});
 item.sidebarTitleOverflow=await page.locator('[data-testid="stSidebarUserContent"]').evaluate(e=>e.scrollWidth>e.clientWidth+2);
 await page.screenshot({path:out+'/'+engine+'-'+width+'-long-title.png',fullPage:true});
 if(item.sidebarTitleOverflow)fs.writeFileSync(out+'/'+engine+'-'+width+'-overflow.json',JSON.stringify(await page.locator('[data-testid="stSidebarUserContent"]').evaluate(e=>({width:e.clientWidth,scrollWidth:e.scrollWidth,overflow:[...e.querySelectorAll('*')].filter(x=>x.getBoundingClientRect().right>e.getBoundingClientRect().right+2).slice(0,15).map(x=>({tag:x.tagName,text:x.textContent?.slice(0,120),width:x.getBoundingClientRect().width,style:getComputedStyle(x).minWidth}))})),null,2));
 if(width<1000&&await closeSidebar.isVisible())await closeSidebar.click();
 await page.getByText('Cowork · Soon' ,{exact:true}).click();
 await page.getByText(/Cowork will be the place/).waitFor();item.coworkHonest=await prompt.isDisabled();
 await page.getByText('Chat',{exact:true}).click();
 await page.locator('.st-key-browser_provider [role="combobox"]').click();
 await page.getByRole('option',{name:'Gemini',exact:true}).click();
 await page.locator('.st-key-provider_information button:visible').first().click();
 await page.getByText('Configured model: fixture-gemini',{exact:true}).waitFor();item.providerInfoMatches=true;
 await page.keyboard.press('Escape');
 item.finalOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+2);
 item.status=item.headerActionsInTopBar&&item.nativeOptionsMenuVisible&&item.developerPromptsHidden&&item.landingClean&&item.providerOnly&&item.attachmentsListOnly&&item.preview&&item.removalKeepsCorrectPreview&&item.chatWorks&&item.firstMessageStartsNewChat&&item.generalOnlyOnSelection&&item.longTitleSaved&&!item.sidebarTitleOverflow&&item.memoryWraps&&item.settingsDropdown&&item.newChatClean&&item.coworkHonest&&item.providerInfoMatches&&!item.initialOverflow&&!item.finalOverflow?'passed':'failed';
 await page.screenshot({path:out+'/'+engine+'-'+width+'-final.png',fullPage:true});
 }catch(e){item.status='failed';item.error=String(e.message).slice(0,700);await page.screenshot({path:out+'/'+engine+'-'+width+'-error.png',fullPage:true}).catch(()=>{});fs.writeFileSync(out+'/'+engine+'-'+width+'-controls.json',JSON.stringify(await page.locator('button').evaluateAll(es=>es.map(e=>({text:e.textContent,label:e.getAttribute('aria-label')}))).catch(()=>[])));}
 results.push(item);console.log(JSON.stringify(item));await page.close();
 }
 }catch(e){results.push({engine,status:'unavailable',error:String(e.message).slice(0,200)});}finally{if(browser)await browser.close();}
}
fs.writeFileSync(out+'/results.json',JSON.stringify({scope:'isolated redesign fixtures; installed Chrome/Edge at emulated viewports, not physical phones',results},null,2));
if(results.length!==(process.env.UI_REDESIGN_FULL?8:2)||results.some(r=>r.status!=='passed'))process.exitCode=1;
})().catch(e=>{console.error(e.message);process.exit(1)});
