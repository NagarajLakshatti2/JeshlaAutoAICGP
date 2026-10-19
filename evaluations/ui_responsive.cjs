const fs=require('fs');
const {chromium}=require('C:/Users/nagar/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/playwright');
const [url,out]=process.argv.slice(2);fs.mkdirSync(out,{recursive:true});
(async()=>{const results=[];
for(const [engine,executablePath] of [['chrome','C:/Program Files/Google/Chrome/Application/chrome.exe'],['edge','C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe']]){
 let browser;
 try{browser=await chromium.launch({executablePath,headless:true,timeout:20000});
 for(const width of [360,390,768,1440]){
  const page=await browser.newPage({viewport:{width,height:900}});
  const item={engine,width};
  try{
   await page.goto(url,{waitUntil:'domcontentloaded',timeout:30000});
   await page.getByRole('heading',{name:'JeshlaAutoAI',exact:true}).waitFor({timeout:30000});
   item.mainOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+2);
   const memory=page.getByText('Shared project memory',{exact:true});
   if(!(await memory.isVisible())){
    const opener=page.locator('[data-testid="stSidebarCollapsedControl"] button, [data-testid="stExpandSidebarButton"], [data-testid="collapsedControl"] button').first();
    await opener.click({timeout:5000});
   }
   await memory.click();
   await page.getByRole('button',{name:'Show saved facts',exact:true}).click();
   const value=page.getByRole('textbox',{name:'long_reference',exact:true});
   await value.waitFor({timeout:15000});
   const box=await value.boundingBox();item.memoryFits=!!box&&box.x>=-2&&box.x+box.width<=width+2;
   item.memoryWraps=await value.evaluate(e=>e.scrollWidth<=e.clientWidth+2);
   item.sidebarOverflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+2);
   item.status=!item.mainOverflow&&item.memoryFits&&item.memoryWraps&&!item.sidebarOverflow?'passed':'failed';
   await page.screenshot({path:out+'/'+engine+'-'+width+'.png',fullPage:true});
  }catch(e){item.status='failed';item.error=String(e.message).slice(0,300);await page.screenshot({path:out+'/'+engine+'-'+width+'-error.png',fullPage:true}).catch(()=>{});}
  results.push(item);await page.close();
 }
 }catch(e){results.push({engine,status:'unavailable',error:String(e.message).slice(0,200)});}finally{if(browser)await browser.close();}
}
fs.writeFileSync(out+'/results.json',JSON.stringify({scope:'synthetic fixtures; desktop engines at emulated viewport sizes, not physical phones',results},null,2));console.log(JSON.stringify(results));})().catch(e=>{console.error(e.message);process.exit(1)});
