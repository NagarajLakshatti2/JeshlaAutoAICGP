"""Deterministic Java template for a reviewed text-entry/clear plan."""
import re

JAVA_TEMPLATE = r'''package __PACKAGE__;

import com.microsoft.playwright.*;
import com.microsoft.playwright.options.*;
import com.fasterxml.jackson.databind.ObjectMapper;
import org.testng.Assert;
import org.testng.annotations.Test;
import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Instant;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Locator/data/URL are runtime plan inputs; no website-specific selector is embedded. */
public class __CLASS__ {
    private String required(String key) {
        String value=System.getProperty(key);
        Assert.assertNotNull(value,"Missing reviewed plan property: "+key);
        Assert.assertFalse(value.isBlank(),"Empty reviewed plan property: "+key);
        return value;
    }
    @Test(description="TI-TC-001: exact required text retention and selected-text clearing")
    public void TI_TC_001_textEntryAndClear() throws Exception {
        String url=required("web.pilot.url"), by=required("web.pilot.by"), target=required("web.pilot.target");
        String value=required("web.pilot.value"), address=required("web.pilot.address");
        String dismiss=System.getProperty("web.pilot.dismiss","");
        Path out=Path.of(required("web.pilot.evidence"));Files.createDirectories(out);
        URI origin=URI.create(url);
        Assert.assertEquals(origin.getScheme(),"https");
        Map<String,Object> data=new LinkedHashMap<>();
        data.put("case_id","TI-TC-001");data.put("started_at",Instant.now().toString());
        data.put("url",url);data.put("locator_by",by);data.put("locator_text",target);
        try(Playwright playwright=Playwright.create()) {
            String pin=address.contains(":")?"["+address+"]":address;
            Browser browser=playwright.chromium().launch(new BrowserType.LaunchOptions().setHeadless(true)
                .setArgs(List.of("--host-resolver-rules=MAP "+origin.getHost()+" "+pin)));
            BrowserContext context=browser.newContext(new Browser.NewContextOptions()
                .setViewportSize(1280,900).setAcceptDownloads(false).setServiceWorkers(ServiceWorkerPolicy.BLOCK));
            context.route("**/*",route->{
                try {
                    URI request=URI.create(route.request().url());
                    String method=route.request().method();
                    if((method.equals("GET")||method.equals("HEAD")) && request.getScheme().equals("https")
                        && origin.getHost().equals(request.getHost()) && request.getUserInfo()==null
                        && (request.getPort()==-1||request.getPort()==443)) route.resume();
                    else route.abort();
                } catch(RuntimeException invalid) {route.abort();}
            });
            context.routeWebSocket("**/*",socket->socket.close());
            Page page=context.newPage();page.setDefaultTimeout(12000);page.setDefaultNavigationTimeout(25000);
            context.tracing().start(new Tracing.StartOptions().setScreenshots(true).setSnapshots(true));
            try {
                Response response=page.navigate(url,new Page.NavigateOptions().setWaitUntil(WaitUntilState.DOMCONTENTLOADED));
                Assert.assertNotNull(response);Assert.assertEquals(response.status(),200);
                data.put("browser",browser.version());
                if(!dismiss.isBlank()) {
                    Locator button=page.getByRole(AriaRole.BUTTON,new Page.GetByRoleOptions().setName(dismiss).setExact(true));
                    button.waitFor(new Locator.WaitForOptions().setState(WaitForSelectorState.VISIBLE));
                    Assert.assertEquals(button.count(),1,"Observed cookie control must remain unique");
                    Assert.assertEquals(button.evaluate("e=>!!e.form"),false,"Do not submit a form");button.click();
                }
                Locator field;
                if(by.equals("label")) field=page.getByLabel(target,new Page.GetByLabelOptions().setExact(true));
                else if(by.equals("placeholder")) field=page.getByPlaceholder(target,new Page.GetByPlaceholderOptions().setExact(true));
                else throw new IllegalArgumentException("Unsupported reviewed locator method");
                field.waitFor(new Locator.WaitForOptions().setState(WaitForSelectorState.VISIBLE));
                Assert.assertEquals(field.count(),1,"Observed field must remain unique");
                Assert.assertEquals(field.evaluate("e=>e.tagName==='INPUT'&&e.type==='text'&&!e.disabled&&!e.readOnly"),true);
                Assert.assertTrue(field.isEditable());field.click();field.fill("");
                data.put("initial_value",field.inputValue());
                page.screenshot(new Page.ScreenshotOptions().setPath(out.resolve("initial.png")));
                Assert.assertEquals(field.inputValue(),"","Independent empty starting state");
                field.fill(value);data.put("entered_value",field.inputValue());
                data.put("placeholder_after_entry",field.evaluate("e=>e.matches(':placeholder-shown')"));
                page.screenshot(new Page.ScreenshotOptions().setPath(out.resolve("entered.png")));
                Assert.assertEquals(field.inputValue(),value,"Complete input value must equal the source data");
                field.press("ControlOrMeta+A");field.press("Backspace");
                data.put("cleared_value",field.inputValue());
                data.put("placeholder_after_clear",field.evaluate("e=>e.matches(':placeholder-shown')"));
                page.screenshot(new Page.ScreenshotOptions().setPath(out.resolve("cleared.png")));
                Assert.assertEquals(field.inputValue(),"","Selected-text Backspace must leave an empty field");
                data.put("status","passed");
            } catch(RuntimeException|AssertionError failure) {
                data.put("status","failed");data.put("error",failure.toString());
                try {page.screenshot(new Page.ScreenshotOptions().setPath(out.resolve("failure.png")));} catch(RuntimeException ignored) {}
                throw failure;
            } finally {
                data.put("finished_at",Instant.now().toString());
                new ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(out.resolve("observations.json").toFile(),data);
                context.tracing().stop(new Tracing.StopOptions().setPath(out.resolve("trace.zip")));
                context.close();browser.close();
            }
        }
    }
}
'''


def text_input_source(test_class, case_id="TI-TC-001"):
    if not isinstance(test_class,str) or not re.fullmatch(r'tests\.web\.[A-Za-z_][A-Za-z0-9_]*',test_class):
        raise ValueError('Choose one class in the target tests.web package.')
    if not isinstance(case_id,str) or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,63}',case_id):
        raise ValueError('Use a simple source case identifier.')
    package,_,name=test_class.rpartition('.')
    method=case_id.replace('-','_')+'_textEntryAndClear'
    return JAVA_TEMPLATE.replace('__PACKAGE__',package).replace('__CLASS__',name).replace('TI-TC-001',case_id).replace('TI_TC_001_textEntryAndClear',method)
