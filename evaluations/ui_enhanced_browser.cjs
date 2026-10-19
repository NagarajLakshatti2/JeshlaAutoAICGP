const fs=require('fs');
const {chromium}=require('C:/Users/nagar/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const [url,out]=process.argv.slice(2);fs.mkdirSync(out,{recursive:true});
(async()=>{const results=[];
for(const [engine,executablePath] of [['chrome','C:/Program Files/Google/Chrome/Application/chrome.exe'],['edge','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe']]){
if(process.env.UI_QUICK_CHECK&&engine!=='chrome')continue;
let browser;
try{browser=await chromium.launch({executablePath,headless:true,timeout:20000});
for(const width of (process.env.UI_SETTINGS_CHECK?[engine==='chrome'?360:1440]:(process.env.UI_QUICK_CHECK?[360]:[360,390,768,1440]))){
 const page=await browser.newPage({viewport:{width,height:900}});const item={engine,width};
 try{
 await page.goto(url,{waitUntil:'domcontentloaded',timeout:30000});
 await page.getByRole('heading',{name:'JeshlaAutoAI',exact:true}).waitFor({timeout:30000});
 await page.getByText('Attach a document',{exact:true}).click();
 await page.locator('input[type=file]').setInputFiles({name:'fixture.txt',mimeType:'text/plain',buffer:Buffer.from('Browser upload evidence '+width)});
 await page.getByRole('button',{name:'Prepare document preview',exact:true}).click();
 const preview=page.getByRole('textbox',{name:'Extracted text preview',exact:true});
 await preview.waitFor({timeout:15000});item.upload=await preview.inputValue()==='Browser upload evidence '+width;
 const prompt=page.getByRole('textbox',{name:'Message JeshlaAutoAI',exact:true});
 await prompt.fill('Summarize this upload');await prompt.press('Enter');
 await page.getByRole('button',{name:'Download this answer',exact:true}).waitFor({timeout:20000});
 const downloadEvent=page.waitForEvent('download');await page.getByRole('button',{name:'Download this answer',exact:true}).click();
 const download=await downloadEvent;const answerPath=out+'/'+engine+'-'+width+'-answer.md';await download.saveAs(answerPath);
 item.answerDownload=fs.readFileSync(answerPath,'utf8').includes('Browser upload evidence '+width);
 if(process.env.UI_SETTINGS_CHECK){
 await page.getByText('Files created by approved actions',{exact:true}).click();
 await page.getByRole('button',{name:'Prepare download',exact:true}).click();
 await page.getByRole('button',{name:'Download approved-export.txt',exact:true}).waitFor();
 const exportEvent=page.waitForEvent('download');await page.getByRole('button',{name:'Download approved-export.txt',exact:true}).click();
 const exported=await exportEvent;const exportPath=out+'/'+engine+'-approved-export.txt';await exported.saveAs(exportPath);
 item.approvedDownload=fs.readFileSync(exportPath,'utf8')==='Approved fixture export';
 }
 if(!(await page.getByText('Shared project memory',{exact:true}).isVisible()))await page.locator('[data-testid="stSidebarCollapsedControl"] button, [data-testid="stExpandSidebarButton"], [data-testid="collapsedControl"] button').first().click();
 await page.getByText('Model settings',{exact:true}).click();
 await page.getByText('Configured model: fixture-model',{exact:true}).waitFor();item.settings=true;
 if(process.env.UI_SETTINGS_CHECK){
 await page.getByText('ollama',{exact:true}).click();
 await page.getByRole('textbox',{name:'Model ID for next restart',exact:true}).fill('fixture-next-model');
 await page.getByText('Save this provider and model to local .env',{exact:true}).click();
 await page.getByRole('button',{name:'Save model settings',exact:true}).click();
 await page.getByText('Saved ollama / fixture-next-model. Restart Streamlit and the console to apply. Environment overrides may take precedence.',{exact:true}).waitFor({state:'attached'});
 item.settingsSave=true;
 }
 await page.keyboard.press('Escape');
 await page.getByText('Shared project memory',{exact:true}).click();
 await page.getByRole('button',{name:'Show saved facts',exact:true}).click();
 const memory=page.getByRole('textbox',{name:'long_reference',exact:true});await memory.waitFor();
 const box=await memory.boundingBox();item.memoryFits=!!box&&box.x>=-2&&box.x+box.width<=width+2;
 item.memoryWraps=await memory.evaluate(e=>e.scrollWidth<=e.clientWidth+2);
 const factKey='browser_check_'+engine+'_'+width;
 await page.getByRole('textbox',{name:'Fact name',exact:true}).fill(factKey);
 await page.getByRole('textbox',{name:'Fact value (for save/update)',exact:true}).fill('verified fixture');
 await page.getByText('I confirm this change to memory shared across my chats',{exact:true}).click();
 await page.getByRole('button',{name:'Apply memory change',exact:true}).click();
 await page.getByText('Saved memory: '+factKey+'.',{exact:true}).first().waitFor();
 await page.waitForFunction(()=>{const input=document.querySelector('input[aria-label="I confirm this change to memory shared across my chats"]');return input&&!input.checked;},{},{timeout:10000});
 item.memoryConfirmationReset=!(await page.getByRole('checkbox',{name:'I confirm this change to memory shared across my chats',exact:true}).isChecked());
 await page.getByText('Search conversation text',{exact:true}).click();
 await page.getByRole('textbox',{name:'Words in messages',exact:true}).fill('Browser upload evidence');
 await page.getByRole('button',{name:'Search saved messages',exact:true}).click();
 await page.getByRole('button',{name:'Open chat: default',exact:true}).first().waitFor();item.search=true;
 item.pageOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+2);
 item.status=(!process.env.UI_SETTINGS_CHECK||(item.approvedDownload&&item.settingsSave))&&item.upload&&item.answerDownload&&item.settings&&item.memoryFits&&item.memoryWraps&&item.memoryConfirmationReset&&item.search&&!item.pageOverflow?'passed':'failed';
 await page.screenshot({path:out+'/'+engine+'-'+width+'.png',fullPage:true});
 }catch(e){item.status='failed';item.error=String(e.message).slice(0,350);await page.screenshot({path:out+'/'+engine+'-'+width+'-error.png',fullPage:true}).catch(()=>{});}
 results.push(item);console.log(JSON.stringify(item));await page.close();
}
}catch(e){results.push({engine,status:'unavailable',error:String(e.message).slice(0,200)});}finally{if(browser)await browser.close();}
}
fs.writeFileSync(out+'/results.json',JSON.stringify({scope:'isolated fixtures; installed desktop Chrome/Edge at emulated sizes, not physical devices',results},null,2));
if(results.length!==(process.env.UI_SETTINGS_CHECK?2:(process.env.UI_QUICK_CHECK?1:8))||results.some(r=>r.status!=='passed'))process.exitCode=1;
})().catch(e=>{console.error(e.message);process.exit(1)});
