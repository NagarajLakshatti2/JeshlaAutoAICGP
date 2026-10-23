"""Configurable native Java test for the reviewed Android text-entry smoke."""
import re

JAVA_TEMPLATE = r"""package __PACKAGE__;

import io.appium.java_client.AppiumBy;
import io.appium.java_client.AppiumClientConfig;
import io.appium.java_client.android.AndroidDriver;
import io.appium.java_client.android.options.UiAutomator2Options;
import org.openqa.selenium.OutputType;
import org.openqa.selenium.WebElement;
import org.testng.Assert;
import org.testng.annotations.Test;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.net.URI;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Duration;
import java.time.Instant;
import java.util.HexFormat;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import javax.xml.XMLConstants;
import javax.xml.parsers.DocumentBuilderFactory;
import org.w3c.dom.Element;
import org.w3c.dom.NodeList;
import java.io.ByteArrayInputStream;
import java.nio.charset.StandardCharsets;

/** Explicit app/device/locator/data inputs; no application-specific selector or root. */
public class __CLASS__ {
    private String required(String key) {
        String value = System.getProperty("mobile.pilot." + key);
        Assert.assertNotNull(value, "Missing reviewed native plan property: " + key);
        Assert.assertFalse(value.isBlank());
        return value;
    }
    private void verifyField(String source, String id) throws Exception {
        DocumentBuilderFactory factory = DocumentBuilderFactory.newInstance();
        factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true);
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_DTD, "");
        factory.setAttribute(XMLConstants.ACCESS_EXTERNAL_SCHEMA, "");
        NodeList nodes = factory.newDocumentBuilder().parse(new ByteArrayInputStream(source.getBytes(StandardCharsets.UTF_8))).getElementsByTagName("*");
        int count = 0;
        for (int i = 0; i < nodes.getLength(); i++) {
            Element element = (Element) nodes.item(i);
            if (id.equals(element.getAttribute("resource-id"))) {
                count++;
                Assert.assertEquals(element.getAttribute("class"), "android.widget.EditText");
                Assert.assertEquals(element.getAttribute("enabled"), "true");
                Assert.assertEquals(element.getAttribute("displayed"), "true");
                Assert.assertEquals(element.getAttribute("password"), "false");
                Assert.assertEquals(element.getAttribute("input-type"), "524289");
            }
        }
        Assert.assertEquals(count, 1, "The inspected ordinary field must remain unique");
    }
    @Test(description="ANDROID-SMOKE-001: exact native text entry and clear", timeOut=240000)
    public void ANDROID_SMOKE_001_textEntryAndClear() throws Exception {
        Path out = Path.of(required("evidence")); Files.createDirectories(out);
        Path apk = Path.of(required("app"));
        String hash = HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(Files.readAllBytes(apk)));
        Assert.assertEquals(hash, required("sha256"), "Reviewed APK bytes must remain unchanged");
        URI server = URI.create(required("server"));
        Assert.assertEquals(server.getScheme(), "http"); Assert.assertEquals(server.getHost(), "127.0.0.1");
        String id = required("field"), expected = required("value");
        Map<String,Object> data = new LinkedHashMap<>();
        data.put("case_id", "ANDROID-SMOKE-001"); data.put("started_at", Instant.now().toString());
        data.put("app_sha256", hash); data.put("field_id", id); data.put("status", "incomplete");
        AndroidDriver driver = null; Throwable primary = null;
        try {
            UiAutomator2Options options = new UiAutomator2Options();
            options.setCapability("appium:udid", required("udid"));
            options.setCapability("appium:app", apk.toString());
            options.setCapability("appium:appPackage", required("package"));
            options.setCapability("appium:appActivity", required("activity"));
            options.setCapability("appium:appWaitActivity", required("activity"));
            options.setCapability("appium:noReset", true); options.setCapability("appium:fullReset", false);
            options.setCapability("appium:autoGrantPermissions", false);
            options.setCapability("appium:newCommandTimeout", 120);
            options.setCapability("appium:adbExecTimeout", 60000);
            options.setCapability("appium:uiautomator2ServerInstallTimeout", 90000);
            options.setCapability("appium:uiautomator2ServerLaunchTimeout", 90000);
            data.put("phase", "session_creation");
            AppiumClientConfig client = AppiumClientConfig.defaultConfig().baseUri(server)
                .connectionTimeout(Duration.ofSeconds(10)).readTimeout(Duration.ofSeconds(60));
            driver = new AndroidDriver(client, options);
            data.put("phase", "native_assertions");
            driver.manage().timeouts().implicitlyWait(Duration.ofSeconds(12));
            data.put("session_id", driver.getSessionId().toString());
            data.put("capabilities", driver.getCapabilities().asMap());
            String source = driver.getPageSource(); Files.writeString(out.resolve("initial-source.xml"), source);
            verifyField(source, id);
            List<WebElement> fields = driver.findElements(AppiumBy.id(id));
            Assert.assertEquals(fields.size(), 1); WebElement field = fields.get(0);
            Assert.assertTrue(field.isEnabled()); Assert.assertTrue(field.isDisplayed());
            field.click(); field.clear(); data.put("initial_value", field.getText());
            Assert.assertEquals(field.getText(), "");
            Files.write(out.resolve("initial.png"), driver.getScreenshotAs(OutputType.BYTES));
            field.sendKeys(expected); data.put("entered_value", field.getText());
            Assert.assertEquals(field.getText(), expected, "Complete native value must match the reviewed data");
            Files.write(out.resolve("entered.png"), driver.getScreenshotAs(OutputType.BYTES));
            field.clear(); data.put("cleared_value", field.getText());
            Assert.assertEquals(field.getText(), "", "Native clear must leave the field empty");
            Files.write(out.resolve("cleared.png"), driver.getScreenshotAs(OutputType.BYTES));
            Files.writeString(out.resolve("final-source.xml"), driver.getPageSource());
            data.put("status", "passed");
        } catch (Exception | AssertionError failure) {
            primary = failure; data.put("status", "failed"); data.put("error", failure.toString());
            if (driver == null) data.put("session_creation_uncertain", true);
            if (driver != null) {
                try { Files.write(out.resolve("failure.png"), driver.getScreenshotAs(OutputType.BYTES)); }
                catch (Exception ignored) { }
            }
            throw failure;
        } finally {
            try {
                if (driver != null) { driver.quit(); data.put("session_closed", true); }
            } catch (RuntimeException cleanup) {
                data.put("status", "failed"); data.put("cleanup_error", cleanup.toString());
                if (primary != null) primary.addSuppressed(cleanup); else throw cleanup;
            } finally {
                data.put("finished_at", Instant.now().toString());
                new ObjectMapper().writerWithDefaultPrettyPrinter().writeValue(out.resolve("observations.json").toFile(), data);
            }
        }
    }
}
"""


def android_text_source(test_class, case_id="ANDROID-SMOKE-001"):
    if not isinstance(test_class, str) or not re.fullmatch(r"tests\.mobile\.[A-Za-z_][A-Za-z0-9_]*", test_class):
        raise ValueError("Choose one class in the target tests.mobile package.")
    if not isinstance(case_id, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,63}", case_id):
        raise ValueError("Use a simple case identifier.")
    package, _, name = test_class.rpartition(".")
    method = case_id.replace("-", "_") + "_textEntryAndClear"
    return (JAVA_TEMPLATE.replace("__PACKAGE__", package).replace("__CLASS__", name)
            .replace("ANDROID-SMOKE-001", case_id).replace("ANDROID_SMOKE_001_textEntryAndClear", method))
