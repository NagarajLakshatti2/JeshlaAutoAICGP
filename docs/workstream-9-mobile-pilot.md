# WS9 9.5 — Android and iOS mobile pilot

**Overall P — Android setup/native smoke Y; scoped Java implementation/compile Y; live Java and iOS execution P — BLOCKED.** Latest integration checkpoint spans 23–24 October 2026.

The user selected the official Appium Android demo and a dedicated emulator, then requested an iPhone/iOS demo too. Selected apps are ApiDemos for Android and UIKitCatalog for iOS. No paid cloud device service or account was configured.

| Deliverable | Status | Evidence or remaining work |
|---|---|---|
| Android prerequisites | Y | Existing Appium 3.8.0, UiAutomator2 8.7.0, Node 24.13.0, Android SDK and usable WHPX; Appium Doctor reports zero required fixes |
| SDK command-line tools | Y | Official download SHA-256 verified; added under existing SDK without updating existing packages |
| Dedicated emulator | Y | Android 15/API 35 AOSP x86_64 image; Jeshla_WS9_API35, serial emulator-5580; actual boot completed |
| Android sample | Y | Official npm android-apidemos 5.0.0 archive SHA-512 verified, APK hash recorded; installed only on pilot emulator |
| Native Appium smoke | Y | TextFields activity, observed unique non-password edit2 field: empty -> Hello World -> empty; screenshots, actual XML, capabilities and closed session |
| Java/Gradle scoped integration | Y — implementation/compile; P — live acceptance | New integrations/mobile adapter and final src/mobileTest/java/tests/mobile/AndroidInputAgentPilotTest.java; clean isolated compile and source-set check;57 offline checks pass. Existing build files unchanged; no native Java pass claimed |
| Native Java execution | P — BLOCKED | First run failed at Appium Settings startup; one host-GPU/smaller-display rerun timed out during session startup. Uncertain receipt retained; no replay. Final bounded HTTP change compiled only |
| Agent-driven mobile planning/action integration | P | This was an explicit development setup smoke through native Appium HTTP, not a deployed console/Streamlit workflow |
| iOS demo source | Y | Official npm ios-uicatalog 3.8.0 archive downloaded and integrity verified; UIKitCatalog selected |
| iOS simulator/device execution | P — BLOCKED | No Mac/Xcode simulator or prepared real iPhone/WDA available; no actual iOS run or signed IPA claimed |

## Actual scope and diagnostics

This native Android smoke checks a simple demo-control contract: an editable ordinary field retains the exact supplied text and becomes empty after clearing. It does not verify application business rules, every control, production apps or the 12-case web test pack. It is not a replacement or migration of the target Java framework.

The first boot exceeded the initial short wait; later actual boot evidence confirmed readiness. The initial native source captured an Appium Settings ANR dialog, so no input pass was claimed. The dedicated emulator display was reduced to 720x1280 at density 320. The next discovery reached TextFields and revealed two controls sharing edit3, so uniqueness validation stopped. Saved discovery contained a unique ordinary unhinted edit2 field; the final check revalidated it and passed exact value equality and clearing. Earlier diagnostics are preserved. No positional selector, password control, forced click or weakened assertion was substituted.

The final Appium session was closed. Pilot processes are stopped after evidence capture; SDK/image/APK and AVD definition remain for reuse. No existing target source file, global Java environment setting or LLM provider configuration was changed. The initial setup needed no new Python implementation. The Java integration now lives in integrations/mobile (plans.py, text_test.py, gradle.py and package __init__.py), with focused tests under tests/test_mobile_pilot.py. It reuses existing agent/actions receipts and report parsing; no flat agent helpers were added.

## Current Android Java integration

The selected native smoke is now represented by a configurable Java/Appium/TestNG test in **src/mobileTest/java/tests/mobile/AndroidInputAgentPilotTest.java**. Keeping it outside src/test/java prevents Appium imports from changing normal web/API compilation. An actual Gradle check confirms that the normal test source set excludes it. Existing build.gradle, testng.xml and inspected pre-existing source hashes are unchanged. The temporary copy created in src/test/java was removed only after verifying its recorded hash and creating the dedicated-source copy.

The adapter validates the saved XML, successful closed native-smoke baseline and APK bytes; it rejects stale files, duplicate IDs, hidden/disabled/password controls, incompatible app/device data and non-loopback Appium endpoints. The isolated task selects only this class, Java17 release compilation, the target's TestNG/Jackson versions and pinned Appium11.0.0/Selenium API4.50.0. It disables ReportPortal, prepares no mixed suite, and grants no execution approval on its own. Current tests and compile verification pass; this does not certify arbitrary native apps or deployed chat planning.

Actual Java live results remain **P — BLOCKED**. Attempt1 failed before field assertions because Appium Settings did not run within30000ms. After changing only the dedicated AVD to host graphics, physical720x1280 display and disabled Vulkan, attempt2 hit the TestNG240s/command300s deadline while creating the UiAutomator2 session. The action receipt is uncertain and retained; no automatic replay. Owned Appium/emulator processes were stopped. No exact-value assertion was weakened, skipped or marked passed.

The final template adds explicit10s connect/60s HTTP read deadlines and records uncertain session creation. It was compiled and checked offline after the failed live attempts; no further device run was made. The first isolated compilation completed its tasks but exceeded a120s wrapper budget; after verifying no owned workers remained, a cached confirmation with240s budget exited0 and verified source isolation. Original timeout receipts remain unchanged.

**Resume conditions:** diagnose/fix Appium Settings and UiAutomator2 startup on a stable emulator, or select a connected Android device under a separately reviewed device policy; then make one fresh reviewed run with a new evidence directory. Do not reinstall unchanged SDK packages, switch LLM providers or replay uncertain receipts to address this local runtime issue. Meanwhile, proceed to9.6 failure investigation using the saved reports/logs. Full agent-chat mobile planning remains a separate P integration scope.

Java evidence: outputs/acceptance/ws9-mobile-java-20261023/{completion.json,plan.json,source-isolation-change.json,compile-reassessment.json,isolated-compile/confirmed-result.json,offline-tests.json,failure-diagnosis.json,native-run/,native-run-v2/,action-receipts.sqlite3,process-cleanup.json,target-source-before.json,target-source-after.json}. Final focused regressions:57 run,57 passed, zero failures/errors/skips, network blocked. Final compile/source-isolation command exited0; the live native Java test did not pass.

## iPhone/iOS boundary

The downloaded iOS package contains source, not a built simulator .app or signed device .ipa. Build a compatible UIKitCatalog simulator .app on a Mac with Xcode, or a properly signed device build for a prepared iPhone. The standard simulator route requires macOS; an IPA cannot run in an Android emulator or the iOS Simulator.

Current XCUITest also documents limited Windows/Linux support for real iOS 18+ devices. That route requires explicit device/version capabilities, RemoteXPC preparation, and already installed or externally managed signed WebDriverAgent. It does not provide a Windows iOS Simulator. Neither route is configured here. Sources: [system requirements](https://appium.github.io/appium-xcuitest-driver/latest/getting-started/system-requirements/), [non-macOS hosts](https://appium.github.io/appium-xcuitest-driver/latest/guides/non-macos-hosts/), [official sample repository](https://github.com/appium/ios-uicatalog), [current iOS monorepo](https://github.com/appium/appium-ios).

## Evidence and reuse

Evidence root: outputs/acceptance/ws9-mobile-pilot-20261023/.

- completion.json and setup-status.json: separate setup, smoke, framework and iOS statuses.
- command-tools.json, image-install.json, avd-create.log and device.json: verified tool/image/boot setup.
- apps/: verified Android APK and Android/iOS source archives with npm integrity and SHA metadata. No npm lifecycle scripts executed.
- native-smoke/, native-smoke-v2/: initial ANR and ambiguous-locator diagnostics.
- native-smoke-v3/: accepted result.json, locator-review.json, initial/final XML, capabilities and three screenshots.
- appium-server.log, appium-doctor.log, emulator.log and display-adjustment.json: runtime diagnostics.
- target-source-preservation.json: existing inspected target files unchanged.
- process-cleanup.json: owned pilot process shutdown result.

For later reuse, use the installed Android SDK emulator with the saved Jeshla_WS9_API35 AVD; allow a cold boot to finish before creating Appium sessions. Use a dedicated loopback Appium port and explicit emulator serial. The saved capabilities include the verified app path; refresh paths if the workspace moves. Do not run the target's mixed default test task merely to test this setup.

Android references: [Appium Android setup](https://appium.io/docs/en/latest/quickstart/uiauto2-driver/), [official Android demo](https://github.com/appium/android-apidemos), [Android SDK tools](https://developer.android.com/studio), [hardware acceleration](https://developer.android.com/studio/run/emulator-acceleration).

The current Markdown roadmap is updated. The Word roadmap remains its earlier snapshot. The initial setup changed environment/evidence only. The later scoped Java integration added the dedicated package/test source and ran57 focused offline checks plus actual compilation/source-set verification. This is not a full default-project regression or mobile release acceptance.
