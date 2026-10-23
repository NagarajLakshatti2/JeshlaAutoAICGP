# WS9 Text Input pilot test pack

Updated 23 October 2026. Project: D:/PlayWrightDemoGradle. Feature selected by the user: Text Input module.

**Current status: 9.0 Y; 9.1 Y for the selected Text Input design pilot.** Revision 2 contains 12 not-run cases covering nine source stories with 35 step/result pairs and six recorded pilot decisions. The design is accepted by the assistant acting under the user's explicit choose-the-best delegation; independent human review is not claimed. Gemini completed one live source read -> rejected quote -> corrected draft -> final answer in four model calls (30.55 seconds). The saved answer clearly states that the test has not been run. The original design pack remains a not_run baseline; user notes and a later actual Chromium TI-TC-001 pass are recorded separately below. Other 11 cases remain not run; wider WS9/release gates are separate.

The selected repository document is the planning source. Feature files and Java code supply implementation evidence, not independent proof that the business rules are correct. QPH case identifiers and the @QAP-3 source tag have not been verified against live Jira.

## Default selection under user delegation

The user asked the assistant to choose the best option and include all useful options where possible. Revision 2 remains the recommended default: all nine selected input types and 12 distinct requirement-backed cases. Preserve allowed alternatives (for example, reject or ignore alphabetic number input) instead of inventing one mandatory UI implementation. Additional input limits or formats remain deferred until specified. Routine technical choices can proceed under this delegation; it does not itself claim independent human review, external action approval or an observed test result.

## Current completion checklist

| Gate | Status | Evidence scope |
|---|---|---|
| 9.0 Project/requirement selection | **Y** | Selected Text Input sources and existing package conventions; read-only setup |
| Requirement clarification and source traceability | **Y** | Six decisions resolved; nine source stories / 12 cases / 35 step checks |
| Revision 2 design acceptance | **Y — delegated** | Accepted under the user's choose-the-best delegation; independent human review not performed |
| Reusable checker and bounded correction | **Y** | Native/legacy compatibility, precise source checks, one matching correction and conservative failure handling |
| Sampled live planning flow | **Y** | Gemini read/check/final, one quote correction; source QPH-001 maps to TI-TC-001 |
| **9.1 Selected Text Input design pilot** | **Y** | Required design and sampled live gates complete within this stated scope |
| 9.2 Observations and defect drafting | **Y — TI-TC-001 observation pilot** | Actual Chromium entry/clear passed after normal overlay dismissal and field click; values/screenshots/timestamps saved. Failure drafts tested offline; no actual defect or external filing |
| Application execution evidence | **One browser case passed; 11 not run** | Direct isolated Playwright TI-TC-001 check; target Gradle suite not run. Deployed agent-chat browser actions remain unconnected |

The live checker still returns P for human/factual/execution checks on its generic draft result and approval_granted false. The scoped design-review decision is recorded separately with its authority; no tool output grants action approval. No claim is made that all 12 cases were generated live or that all three providers passed the live flow. Completion evidence is in outputs/acceptance/ws9-9-1-pilot-completion-20261023.

## Pilot scope and success criteria

- Read the selected project and requirement sources; preserve the target project and its existing uncommitted work.
- Preserve source references and hashes, cover every selected story, separate assumptions and unresolved expectations, and prevent duplicate cases or invented limits.
- Review expected versus actual behavior explicitly; begin every case as not run.
- The 12-case design review is complete under delegation. Review and approve separately scoped code changes/execution before carrying out any action.

## Verified project structure

Build files declare Java 17, Gradle, Playwright, Cucumber, TestNG, Spring and REST Assured. Versions are declarations, not a successful dependency-resolution/build claim. Existing web packages are src/main/java/web/pages and src/test/java/stepdefinitions; the selected runner is runners.QAPracticeHubTestRunner. The root testng.xml also selects API tests, so a default whole-suite invocation is not the selected pilot. The testsuites/testng-web.xml file is empty. No runner was invoked.

The README suggests Ollama, but the inspected WebHooks.java has its LlmGateway import and summarizeFailure call commented out. This read-only pilot has no model/Ollama dependency; no service was started. Existing local changes in the automation repository were retained.

## Source register

| ID | File relative to the selected project | Use |
|---|---|---|
| SPEC | qapracticehub-test-cases.md | Module lines 12-144 are the selected requirements/test expectations |
| FEATURE | src/test/resources/features/qapracticehub/Text Input Module.feature | Two existing Text Input scenarios; not execution evidence |
| STEPS | src/test/java/stepdefinitions/qapracticehub/InputValidationSteps.java | Actual current assertions |
| PAGE | src/main/java/web/pages/qapracticehub/QAPracticeHubHomePage.java | Current selectors and validation helpers |
| RUNNER | src/test/java/runners/QAPracticeHubTestRunner.java | Current feature/glue selection |
| BUILD | build.gradle | Declared stack and runner/tag configuration |
| SUITE | testng.xml | Default runner selection |
| NAV | src/test/java/stepdefinitions/qapracticehub/NavigationSteps.java | Configurable application URL loading |
| HOOKS | src/test/java/stepdefinitions/hooks/WebHooks.java | Current hook dependencies and disabled model call |
| README | README.md | Project overview; setup instructions may be stale |

Hashes and exact file/line references are retained in outputs/acceptance/ws9-text-input-pilot-20261023/sources.json and test-pack.json.

## Coverage matrix

| Requirement | Existing source case | Draft case IDs | State |
|---|---|---|---|
| TI-R01 Basic text entry and clearing | QPH-001 | TI-TC-001 | Passed in isolated Chromium; see separate execution ledger |
| TI-R02 Valid and invalid email handling | QPH-002 | TI-TC-002, TI-TC-003 | Not run |
| TI-R03 Password masking and retained input value | QPH-003 | TI-TC-004 | Not run |
| TI-R04 Number input constraints | QPH-004 | TI-TC-005, TI-TC-006 | Not run |
| TI-R05 Date selection and display | QPH-005 | TI-TC-007 | Not run |
| TI-R06 Phone input with country code | QPH-006 | TI-TC-008, TI-TC-009 | Not run |
| TI-R07 Multiline textarea entry and clearing | QPH-007 | TI-TC-010 | Not run |
| TI-R08 Read-only input preserves existing value | QPH-008 | TI-TC-011 | Not run |
| TI-R09 Disabled input prevents interaction | QPH-009 | TI-TC-012 | Not run |


## Coverage by input type — revision 2

| Input type | In-scope cases | Requirement-based coverage | Extra rules outside the current scope |
|---|---|---|---|
| Basic text | 001 | Exact supplied text; clear to empty | Required/whitespace, Unicode and maximum length |
| Email | 002-003 | Valid/invalid source samples; blur; field-specific feedback | Extra address formats, empty/required and exact error text |
| Password | 004 | Display masking and field value retention | Password strength, minimum length, backend storage |
| Number | 005-006 | Accept 123; reject/ignore abc from empty state | Decimal, sign, exponent, min/max |
| Date | 007 | Select source sample; underlying ISO value; localized display allowed | Allowed ranges, impossible-date entry and other locales |
| Phone | 008-009 | India +91; ten-digit sample; nine-digit negative boundary after blur | More than ten digits, letters and other countries |
| Multiline | 010 | Retain both proposed lines and line break; clear to empty | Maximum length, long-line wrapping and normalization policies |
| Read-only | 011 | Observed original value remains after attempted user typing | Programmatic changes and unspecified paste/selection policies |
| Disabled | 012 | Disabled state/attribute; ordinary interaction blocked; value unchanged | Focus/accessibility behavior and dynamic enablement |

The additional rules listed above are not invented expected outcomes and are not claimed as tested. They can become extra cases once their requirements are supplied. The nine selected source stories are covered; this is not exhaustive coverage of every possible input value, security check, device or browser.

## Pilot decisions and remaining clarifications

The rules below are selected pilot requirements, not observations of the application. The user explicitly accepted the four proposed remaining rules on 23 October 2026. All six recorded questions are resolved; current application support remains unverified.

### TI-D01 Email validation trigger

Under the user's explicit delegation, validate when the email input loses focus (blur). A valid email retains the typed value and has no email-associated error or invalid state after blur. This resolves TI-Q01; it does not impose a rule on other applications.

### TI-D02 Invalid email outcome

The user explicitly chose mandatory email-specific validation. After blur, invalid-email must produce a message associated with that field or a verifiable invalid state of that field. A global unrelated error or checking the retained invalid string alone is insufficient. Exact message text remains unconstrained. This resolves TI-Q02 for the pilot.

### TI-D03

Password checks cover masking and retention of the supplied value in the input field only; backend persistence or credential storage is outside this pilot.

Source: explicit user acceptance of the four proposed pilot rules. Requirement decision only; application behavior unobserved.

### TI-D04

The numeric input must reject or ignore alphabetic input. Starting from an empty field, attempting abc must not leave alphabetic text as an accepted field value.

Source: explicit user acceptance of the four proposed pilot rules. Requirement decision only; application behavior unobserved.

### TI-D05

Compare the underlying selected date value in YYYY-MM-DD form. The visible display may follow the browser locale; do not assert one localized display string.

Source: explicit user acceptance of the four proposed pilot rules. Requirement decision only; application behavior unobserved.

### TI-D06

For the selected India +91 phone field, accept ten digits and require a phone-field-specific invalid state for nine digits after blur. Application support and exact UI indicators remain unobserved.

Source: explicit user acceptance of the four proposed pilot rules. Requirement decision only; application behavior unobserved.

### TI-Q03

Does password stored correctly mean retaining the typed value in the input only? Backend persistence or credential storage is not specified.

**Y — Resolved by TI-D03 (explicit user acceptance).** Password checks cover masking and retention of the supplied value in the input field only; backend persistence or credential storage is outside this pilot. Application behavior has not been observed.

Affected cases: TI-TC-004. Sources: SPEC:54-58.

### TI-Q04

For abc in the numeric field, must the input ignore the characters, reject entry, or retain text and show validation? Confirm the required observable outcome.

**Y — Resolved by TI-D04 (explicit user acceptance).** The numeric input must reject or ignore alphabetic input. Starting from an empty field, attempting abc must not leave alphabetic text as an accepted field value. Application behavior has not been observed.

Affected cases: TI-TC-006. Sources: SPEC:69-73.

### TI-Q05

What date display format and locale should this test assert? The source says correct format without defining it.

**Y — Resolved by TI-D05 (explicit user acceptance).** Compare the underlying selected date value in YYYY-MM-DD form. The visible display may follow the browser locale; do not assert one localized display string. Application behavior has not been observed.

Affected cases: TI-TC-007. Sources: SPEC:83-87.

### TI-Q06

What indicates acceptance of the India +91 ten-digit phone value, and what must occur for nine digits? The shorter-value validation step is conditional and has no explicit expected rejection.

**Y — Resolved by TI-D06 (explicit user acceptance).** For the selected India +91 phone field, accept ten digits and require a phone-field-specific invalid state for nine digits after blur. Application support and exact UI indicators remain unobserved. Application behavior has not been observed.

Affected cases: TI-TC-008, TI-TC-009. Sources: SPEC:97-102.

## Detailed manual cases — revision 2

Revised at the user's request across all nine selected input types. Original case IDs, source priorities and six agreed decisions are preserved. Every row is a planned action and expected outcome; no row is an actual test result. **Design review Y — accepted under user delegation. Execution: not run.**

Reset editable fields as stated so cases are independent. For read-only and disabled controls, record the original value and retain their protections. Identify controls from the real application when execution is separately selected; no live locator or behavior is claimed here.

### TI-TC-001 Enter the specified text and clear the input

Requirement: TI-R01. Source: SPEC:15-29. Priority: High.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: not run. Actual result: none.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"text": "Hello World"}`. Origin: source_sample.

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the basic text input and reset it to an empty starting value. | The intended editable text input is identified and the test starts without leftover text. | Test setup; no new business rule |
| 2 | Enter Hello World and inspect the complete input value. | The complete value equals Hello World; a merely nonempty or different value is insufficient. | SPEC:24-25 |
| 3 | Clear the same input and inspect its value. | The value is empty after clearing. | SPEC:26-28 |

Existing automation evidence: FEATURE lines 3-10 declare this scenario with tag @QAP-3. STEPS lines 32-33 only check non-null/nonempty; they do not assert exact equality. The tag is not verified against live Jira.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-002 Accept the supplied valid email

Requirement: TI-R02. Source: SPEC:31-44. Priority: High.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: not run. Actual result: none.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"email": "test@example.com"}`. Origin: source_sample.

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the email input, focus it and remove any previous value. | The intended email input is identified and ready for the supplied sample. | Test setup; no new business rule |
| 2 | Enter test@example.com, then move focus away without submitting the form. | The email field loses focus after the supplied sample is entered; validation is observed at blur. | SPEC:40-41; TI-D01 |
| 3 | Inspect the retained value and any validation signal associated with this email field. | The value remains test@example.com and there is no email-associated validation error or invalid state after blur. | SPEC:40-44; TI-D01 |

Existing automation evidence: FEATURE lines 15-16 include valid email in a combined scenario; STEPS lines 59-60 check absence of a broadly located error. No run performed.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-003 Validate the supplied invalid email

Requirement: TI-R02. Source: SPEC:31-44. Priority: High.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: not run. Actual result: none.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"email": "invalid-email"}`. Origin: source_sample.

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the email input and remove any previous value, including a valid email from another case. | The negative case starts independently; the supplied invalid email will replace rather than append to old data. | Test setup; no new business rule |
| 2 | Enter invalid-email, then move focus away without submitting the form. | Validation is observed after this email field loses focus. | SPEC:42-44; TI-D01; TI-D02 |
| 3 | Inspect a message or invalid-state indicator specifically associated with the email field. | An email-specific error message or verifiable field invalid state is present. An unrelated page error or retained text alone is insufficient; exact message wording is unconstrained. | SPEC:42-44; TI-D02 |

Existing automation evidence: FEATURE lines 17-18 require a validation error. STEPS lines 75-78 assert only the invalid string value; the validation assertion is commented out.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-004 Mask the password input and verify intended value retention

Requirement: TI-R03. Source: SPEC:46-58. Priority: High.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: not run. Actual result: none.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"password_sample": "password123"}`. Origin: source_sample.

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the password input, clear any existing value and enter the supplied password123 sample. | The supplied sample is entered into the intended password field independently of earlier cases. | SPEC:54-55 |
| 2 | Inspect the displayed password characters. | The displayed password is masked; the sample is not displayed as ordinary readable text. | SPEC:56-56 |
| 3 | Compare the retained input value with password123 through the field value check. | The input retains the supplied value. This checks the field only; backend persistence or credential storage is outside the pilot. | SPEC:57-58; TI-D03 |

Existing automation evidence: No corresponding scenario was found in the selected Text Input Module.feature; no runtime coverage claim.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-005 Accept the supplied numeric input

Requirement: TI-R04. Source: SPEC:60-73. Priority: Medium.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: not run. Actual result: none.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"number": "123"}`. Origin: source_sample.

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the numeric input and clear any existing value. | The correct numeric field starts empty so prior data cannot satisfy this check. | Test setup; no new business rule |
| 2 | Enter 123 and inspect the resulting numeric value. | The numeric value 123 is accepted and retained; a different nonempty value does not satisfy the case. | SPEC:69-70 |

Existing automation evidence: No corresponding scenario was found in the selected Text Input Module.feature; no runtime coverage claim.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-006 Handle the supplied alphabetic value in the number field

Requirement: TI-R04. Source: SPEC:60-73. Priority: Medium.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: not run. Actual result: none.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"text": "abc"}`. Origin: source_sample.

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the same numeric input and clear it to an empty value. | The invalid-input case starts empty and independently of the positive numeric case. | Test setup; no new business rule |
| 2 | Attempt ordinary user entry of abc and record whether entry is rejected or the letters are ignored. | The control rejects or ignores the alphabetic entry; the requirement permits either behavior. | SPEC:71-73; TI-D04 |
| 3 | Inspect the resulting field value after the attempted entry. | The initially empty field remains empty; alphabetic text is not retained as an accepted numeric value. No specific error message is required. | SPEC:71-73; TI-D04 |

Existing automation evidence: No corresponding scenario was found in the selected Text Input Module.feature; no runtime coverage claim.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-007 Select the sample date and inspect its display

Requirement: TI-R05. Source: SPEC:75-87. Priority: Medium.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: not run. Actual result: none.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"date": "2026-09-25"}`. Origin: source_sample.

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the date input and open its date picker. | The intended date control and picker are identified for the selected environment. | SPEC:83-84 |
| 2 | Select the supplied 2026-09-25 sample through the picker. | The sample date is selected. An unavailable sample or missing picker is recorded as an observation to review, not silently replaced by an invented date rule. | SPEC:85-85 |
| 3 | Inspect the selected value and the displayed date. | The underlying value is 2026-09-25 in YYYY-MM-DD form and the display represents that date. Localized display is allowed; no fixed locale-specific string is imposed. | SPEC:86-87; TI-D05 |

Existing automation evidence: No corresponding scenario was found in the selected Text Input Module.feature; no runtime coverage claim.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-008 Accept a ten-digit phone value with the specified country code

Requirement: TI-R06. Source: SPEC:89-102. Priority: Medium.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: not run. Actual result: none.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"country_code": "+91", "phone": "9876543210"}`. Origin: source_sample.

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the phone field, select or confirm India (+91), and clear any previous subscriber value. | The selected country is India (+91) and no previous number can satisfy the positive case. | SPEC:97-97 |
| 2 | Enter the supplied ten-digit subscriber value 9876543210 and move focus away. | The supplied ten-digit subscriber value is entered under the selected India country code. | SPEC:98-99; TI-D06 |
| 3 | Inspect the retained subscriber value and validation state associated with this phone field. | The supplied ten-digit value is accepted and retained, with no phone-field invalid state after blur. | SPEC:98-102; TI-D06 |

Existing automation evidence: No corresponding scenario was found in the selected Text Input Module.feature; no runtime coverage claim.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-009 Validate the nine-digit phone sample after blur

Requirement: TI-R06. Source: SPEC:89-102. Priority: Medium.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: not run. Actual result: none.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"country_code": "+91", "phone": "987654321", "digits": 9}`. Origin: Proposed nine-digit data derived from the source ten-digit example; it is not a new business rule..

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the India (+91) phone field and clear its current subscriber value. | The short-value case starts independently, without the previous ten-digit sample. | SPEC:97-97 |
| 2 | Enter the proposed nine-digit value 987654321 and move focus away. | The nine-digit sample is entered and this phone field loses focus before validation is checked. | SPEC:100-101; TI-D06 |
| 3 | Inspect the invalid state specifically associated with the phone field. | A phone-field-specific invalid state is present after blur. An unrelated page error or the retained short value alone does not satisfy validation; exact message text is unconstrained. | SPEC:100-102; TI-D06 |

Existing automation evidence: No corresponding scenario was found in the selected Text Input Module.feature; no runtime coverage claim.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-010 Enter two lines and clear the textarea

Requirement: TI-R07. Source: SPEC:104-116. Priority: Medium.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: not run. Actual result: none.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"text": "First line\nSecond line"}`. Origin: Proposed synthetic two-line data; the source specifies multiline entry and clearing but no literal sample..

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the textarea and reset it to an empty value. | The intended multiline control starts empty. | Test setup; no new business rule |
| 2 | Enter the proposed two-line sample: First line followed by a line break and Second line. | Both sample lines appear in order with their separating line break; a single joined line or missing content is insufficient. | SPEC:113-114 |
| 3 | Clear the textarea and inspect its content. | The textarea is empty after clearing. | SPEC:115-116 |

Existing automation evidence: No corresponding scenario was found in the selected Text Input Module.feature; no runtime coverage claim.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-011 Preserve the prefilled read-only value

Requirement: TI-R08. Source: SPEC:118-130. Priority: Low.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: not run. Actual result: none.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"replacement_attempt": "Changed value"}`. Origin: Proposed replacement text for an edit attempt; the starting value must be observed, not guessed..

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the prefilled read-only input and record its exact original value. | The baseline is observed from the selected environment, not invented from a fixed example. | SPEC:126-129 |
| 2 | Attempt ordinary keyboard entry of the proposed Changed value text without removing read-only protection or changing DOM attributes. | Ordinary user typing does not edit the read-only control. | SPEC:127-128 |
| 3 | Compare the displayed/input value with the recorded baseline. | The original value remains unchanged and displayed; unrelated field values do not satisfy the assertion. | SPEC:128-130 |

Existing automation evidence: No corresponding scenario was found in the selected Text Input Module.feature; no runtime coverage claim.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

### TI-TC-012 Prevent interaction with the disabled input

Requirement: TI-R09. Source: SPEC:132-144. Priority: Low.

**Design acceptance: Y — user-delegated review. Independent human review: not performed. Execution: not run. Actual result: none.**

Preconditions:

- Use the selected QA Practice Hub environment and navigate to its Inputs section, as required by SPEC.
- Record the environment and browser for a future run. Application availability, live controls and locators remain unverified.
- Keep cases independent: reset editable fields only as stated; record read-only/disabled baselines without changing their protections.

Test data: `{"typing_attempt": "New text"}`. Origin: Proposed synthetic typing-attempt data; no fixed initial field value is assumed..

| Step | Planned action | Expected observable result | Basis |
|---|---|---|---|
| 1 | Locate the disabled input and record its initial value and disabled state. | The intended disabled control and its initial value are identified without assuming fixed content. | SPEC:140-143 |
| 2 | Attempt ordinary clicking and typing of the proposed New text sample, without force-enabling the control. | The disabled control is not available for ordinary user interaction; no forced interaction is used as a substitute. | SPEC:141-142 |
| 3 | Inspect the disabled attribute and compare the final value with the recorded initial value. | The disabled attribute is present and the attempted interaction has not changed the original value. | SPEC:142-144 |

Existing automation evidence: No corresponding scenario was found in the selected Text Input Module.feature; no runtime coverage claim.

Expected-result provenance: source/decision/setup distinctions are listed per step. Source membership checks do not establish observed behavior or business approval.

## Static findings requiring a reviewed follow-up

These are source-inspection findings or risks. They are not reproduced application defects or results of a test run.

### TI-F01 Wrong nonempty text can satisfy the current text-entry check

Priority: High. Classification: static assertion gap. Source: SPEC:24-28, FEATURE:7-10, STEPS:28-34.

The expected input is Hello World, but the step asserts only non-null and length greater than zero.

Proposed next change: After review, retain the entered value in scenario-scoped state and assert exact equality. Do not hardcode Hello World into a reusable step.

Applied: no. Runtime reproduction: no.

### TI-F02 Invalid-email scenario does not assert a validation result

Priority: High. Classification: static assertion gap. Source: FEATURE:17-18, STEPS:63-78.

The step computes error/invalid-state flags and then asserts only the string value; the actual validation assertion is commented out.

Proposed next change: Resolve TI-Q01 and TI-Q02, then assert the confirmed field-specific validation outcome. Keeping the input string alone does not verify validation.

Applied: no. Runtime reproduction: no.

### TI-F03 Email validation lookup can match another visible error

Priority: Medium. Classification: potential false positive. Source: PAGE:26-28, PAGE:59-60.

The fallback selectors include generic visible error and invalid classes instead of restricting every fallback to the email field.

Proposed next change: Inspect the actual permitted application and scope the chosen validation signal to the intended field before using it as an oracle.

Applied: no. Runtime reproduction: no.

### TI-F04 Invalid-email outcome is conditional in steps and mandatory in expected results/Gherkin

Priority: High. Classification: requirement conflict. Source: SPEC:42-44, FEATURE:17-18.

The existing document says validation error if present, but its expected result and the Gherkin require validation.

Resolution: TI-D01 and TI-D02 settle this requirement conflict for the pilot. Mandatory email-field validation after blur is the selected requirement. The original document/feature and Java assertions remain unchanged.

Applied: no. Runtime reproduction: no.

## Deferred coverage

- Required/empty/whitespace rules for text and email are unspecified.
- Text/textarea maximum lengths are unspecified; confirm a limit before designing L-1/L/L+1 expected outcomes.
- Unicode/paste/trim/normalization rules are unspecified.
- Number min/max, sign, decimal and exponent rules are unspecified.
- Phone values above ten digits and international-country behavior need an agreed scope.
- Date minimum/maximum and supported locale policy are unspecified.
- Accessibility and browser/device matrix need separate acceptance criteria.

## Evidence history — earlier checkpoints

The sections below preserve their status at the time recorded. Their earlier P/blocked entries are superseded for the selected 9.1 pilot by the current completion checklist above. Broader WS1-WS8, factual-quality and execution limits retain their stated scope.

## Initial acceptance checkpoint

- Y Selected the actual project and feature with the user; inspected relevant source and package conventions.
- Y Produced a source-linked draft and checked complete story mapping, unique case IDs and unchanged inspected source hashes.
- Y Resolve TI-Q01 and TI-Q02 for the selected email pilot using explicit user/delegated decisions.
- Y Resolve all six recorded questions using the original email decisions and the four newly accepted pilot rules.
- P Complete human/semantic review of the 12 cases and accept the intended assertions.
- Y Implement the reusable read-only source-plan checker in agent/tools/test_plans.py, with existing ProjectTools, policy and shared runtime wiring; mocked agent integration and real-source checks pass.
- P Accept live AI-generated requirement-to-test-pack planning and human/factual review; offline integration does not close that gate.
- X Generate or change target automation code under the selected project packages.
- X Execute selected tests and collect fresh run evidence.

No application, Gradle suite, Jira authentication, provider request or Ollama request was performed. The automation project was not modified. All WS1-WS8 statuses retain their existing scope.

## Reusable source-plan checker checkpoint — 23 October 2026

| Item | Status | Evidence / remaining boundary |
|---|---|---|
| Correct package placement | **Y** | Implementation in existing agent/tools/test_plans.py; thin ProjectTools wrapper; tool classification in agent/policies/tool_registry.py; shared schema/handler in agent/runtime/conversation.py; project instructions in agent/langgraph/langgraph_agent.py. No new flat agent-root module or unnecessary subpackage |
| Bounded draft structure and local source checks | **Y** | Unique IDs, registered fields, required outcomes/questions, bounded case/source counts, project path restrictions, exact quoted spans, SHA256 revision checks and changed-source rejection |
| Draft-only result policy | **Y** | Structure/source-traceability can be Y; factual correctness, human review and execution stay P. All cases remain not_run, actual_result null and approval_granted false |
| Agent registration and compatibility | **Y** | New checker is read-only in both existing project and shared conversation registries. Mocked shared conversation reads requirements and checks a draft without provider/search/Jira/action execution |
| Current pilot source acceptance | **Y** | All 12 existing cases checked in three batches of four against the unchanged specification hash; each result remains a draft. Email decision provenance is preserved separately from repository quotes |
| Live AI-generated plan and semantic review | **P** | No live provider generation/selection acceptance in this milestone. Matching a quote does not prove an expected outcome follows from it or that the source is approved |
| Recorded requirement decisions | **Y** | All six original questions resolved with explicit decision provenance; all 12 cases ready for human review |
| Human acceptance | **P** | Test design is ready for review; no human/factual acceptance or actual application result is inferred |
| Target application tests and fresh run evidence | **P** | No target code edits, app/Gradle run or observed execution results in this step |

Acceptance evidence: outputs/acceptance/ws9-test-plan-tool-20261023. The focused suite ran 77 tests with no failures/errors and one Windows symlink-permission skip. The compatibility suite ran 50 tests: 49 passed and one Streamlit AppTest timed out at its existing 10-second limit. That exact decline test passed on one isolated rerun without changing the timeout or application code; retain the initial timeout as a repeatability observation. After adding the project-tool contract, all 43 final affected tests completed without failures/errors, with the same symlink-permission skip. These are focused results, not a full-suite/release pass.

The existing shared conversation tool-output limit still applies. The real pilot used small batches whose results fit that limit; the checker does not establish unlimited-size plan delivery. The existing pilot test-pack.json retains the original decision records and all cases as not run. Provider configuration, action approvals, Jira authentication, Ollama parking and WS1-WS8 statuses are unchanged. Markdown checkpoints were updated; the Word diagram remains its previous snapshot.



## Confirmed pilot rules checkpoint — 23 October 2026

- **Y** — User accepted TI-D03 through TI-D06: password field value/masking only; reject/ignore numeric letters; underlying ISO date comparison with localized display allowed; India phone ten-digit acceptance and nine-digit field validation after blur.
- **Y** — Updated exactly five affected cases; the other seven case records and source hashes are unchanged. All 12 passed bounded structure/source checks again and have no unresolved recorded questions.
- **P** — Human/semantic review of the completed draft and observed application behavior. Every case is still not run.
- **P** — Live AI-generated planning: the user subsequently approved this exact excerpt/path and generated draft/check results for all three hosted providers. The bounded check and one changed-path recheck ran; the latter reached OpenRouter, Groq and Gemini, but no validated plan completed within its four-call budget. The initial automatic-review rejection is historical; authorization is no longer the blocker.

The reusable live acceptance entry point is evaluations/test_plan_live.py in the existing evaluations area. It confines model tools to the selected source read and draft checker, caps model calls, disables local Ollama for the evaluation process, and uses an external 100-second controller deadline. No persistent provider setting or target code was changed. New verification: outputs/acceptance/ws9-pilot-rules-live-20261023/rule-verification.json. WS9 stage 9.1 remains P for its remaining review/live gates; the earlier checker milestone remains Y within its scope.


## Approved hosted check and fallback fix — 23 October 2026

- **Y** — The user explicitly authorized the reviewed 15-line text-entry excerpt, project path and generated draft/check results for OpenRouter, Groq and Gemini.
- **Y** — Reproduced and fixed a missing read-only fallback registration: agent/providers/tools.py now recognizes read_file and validate_test_plan for the existing bounded compatibility/failover mechanism. Mixed write/approval/memory-proposal registries remain excluded; no persistent provider configuration changed.
- **Y** — Affected offline suite: 94 run, 93 passed, one Windows symlink-permission skip, zero failures/errors. The new regression failed before the fix and passes afterward; it also checks that existing source evidence is preserved on provider switch.
- **Y** — Live fallback observed: OpenRouter quota -> Groq successful requirement read -> Groq quota -> Gemini response. The first run stopped at Groq TOOL_OUTPUT; both original and changed-path results are retained.
- **P** — Live planning completion: the changed-path run took 23.48 seconds and reached its four-model-call budget without an accepted checked draft. Tool names were recorded, but rejected argument/error details were not retained in that version, so the exact validation rejection cause is not established. No third hosted attempt was made.
- **Y** — Evaluation diagnostics now retain rejected checker arguments and their static validation errors. A synthetic offline check verified this logging and confirmed an invalid draft remains unaccepted. This diagnostic improvement is not a live-planning pass.
- **P** — Next technical gate: diagnose the rejected draft format from the new records in a separately bounded check, then verify one complete read -> checked draft -> final answer. Preserve the source checks and actual not-run labels. Human/semantic acceptance of all 12 cases and target execution remain pending.

Evidence: outputs/acceptance/ws9-pilot-rules-live-20261023/hosted-checkpoint.json, fallback-offline.json, live.json, after-fallback-fix/live.json and diagnostic-offline-check.json. The selected source hash is unchanged. No target file changes, test/application/Gradle execution, Jira authentication or Ollama request occurred. Stage 9.1 remains P; WS1-WS8 statuses and the earlier Word snapshot are unchanged.


## Bounded provider diagnostic and local design review — 23 October 2026

- **Y** — Ran the next requested diagnostic on the same explicitly approved excerpt; completed in 11.99 seconds (12.37 including controller). The source hash is unchanged.
- **P — BLOCKED** — Live planning: OpenRouter rate/quota limit, Groq TOOL_OUTPUT after its bounded recovery, then Gemini HTTP 503 PROVIDER_TEMPORARY. The run read the selected requirement but returned no new plan to the local checker. No draft-format cause was established; changing validation rules without that evidence would be speculative. No additional hosted attempt was made in this step.
- **Y** — Completed a local assistant design review of all 12 cases against all nine selected stories and the six explicit/delegated pilot decisions. The audit separates original requirement support from user decisions, confirms source sample/proposed test data provenance, and checks that invented limits/backend persistence/actual results were not added. This is an agent review, not user acceptance or application verification.
- **P** — User acceptance of the 12-case design is requested in this chat. Keep the existing pending_human_review state until an explicit reply; approving the case design does not authorize or claim test execution.

Evidence: outputs/acceptance/ws9-pilot-rules-live-20261023/diagnostic-with-rejections/{live.json,controller.json,checkpoint.json,local-design-review.json}. Stage 9.0 remains Y; stage 9.1 remains P for user design acceptance and a successful complete live planning flow. No production-code change was justified by this provider-blocked diagnostic. No automation-project file, app/test execution, Jira connection, Ollama setting or provider configuration was changed. Next: record the user's design decision, then make at most one unchanged live sample when hosted availability permits; avoid repeated broad tests or schema relaxation.


## All-input-types revision checkpoint — 23 October 2026

- **Y** — Implemented the user's request to revise all selected types according to requirements: 12 revised cases, nine input types, 35 action/expected-result pairs with source/decision/setup provenance.
- **Y** — Preserved all case IDs, original requirements, priorities, sample data, six prior decisions and deferred coverage. Every case has an independent starting state or an observed protected-field baseline; error checks are field-specific where required.
- **Y** — Validated the revised draft locally in four bounded batches. Exact cited source excerpts and hashes still match; all nine requirement IDs map to cases; original source and target project are unchanged.
- **P** — User re-review/acceptance of revision 2. The earlier request for changes has been implemented, not converted into approval. All cases remain pending_human_review and not_run; no actual result or receipt is fabricated.
- **P — BLOCKED** — Complete live AI planning remains at the last recorded provider blocker (OpenRouter quota, Groq tool-output rejection, Gemini HTTP 503). No hosted retry, application/Gradle run, Jira authentication or Ollama request occurred for this revision.

Structured case details remain in outputs/acceptance/ws9-text-input-pilot-20261023/test-pack.json (design_revision 2). Verification and the pre-revision backup are in outputs/acceptance/ws9-all-input-types-revision-20261023. No new Python module or runtime behavior was needed for this case-design revision. WS9 9.0 stays Y; 9.1 remains P for re-review/live acceptance. Word and WS1-WS8 statuses retain their prior scope.


## Bounded plan-correction task checkpoint — 23 October 2026

- **Y** — Implemented specific, trusted validation feedback in the existing tools/runtime packages. TestPlanValidationError retains ValueError compatibility; only validator-authored messages are exposed for correction. Arbitrary backend errors keep the generic safe response.
- **Y** — The shared conversation runtime permits one correction of a rejected draft, preserving case identities and source files. A matching complete visible checker result can resolve that draft rejection; a second invalid attempt stops with an incomplete result. Earlier unrelated tool failures are not erased.
- **Y** — Unrelated case IDs, changed source files, malformed original scope, truncated results and forged approvals cannot turn the pending draft into a completed check. Every accepted checked draft still has human/factual/execution P and cases not_run.
- **Y** — Reproduced two pre-fix failures, then ran the affected offline suite: 208 run, 207 passed, one Windows symlink-permission skip, zero failures/errors. This is focused compatibility coverage, not a full release pass.
- **Y** — Separate real-source/offline-model acceptance completed read -> deliberate quote rejection -> one matching correction -> final draft in four mocked model calls. The source hash is unchanged and no hosted request or application test ran.
- **P** — WS9 stage 9.1 live-provider planning and design acceptance keep their prior scope. The latest hosted blocker remains the last recorded provider/quota/format/503 result; it was not rechecked during this offline task. The new correction behavior has not been live-certified.

Package placement: agent/tools/test_plans.py holds the strict validator and typed error; the new helper agent/runtime/test_plan_feedback.py holds correction-state policy; agent/runtime/conversation.py wires it into the existing shared loop. Tests extend tests/test_test_plans.py. No new subpackage was necessary. Existing project-action tools and approvals retain their behavior; this correction component is scoped to shared conversation, not a rewrite of every project-action loop.

Evidence: outputs/acceptance/ws9-bounded-plan-correction-20261023/{affected-offline.json,affected-offline.log,pilot-correction-offline.json,before/}. Selection policy is recorded in the original test-pack.json. No provider order/settings, target project files, Jira connection, Ollama status or WS1-WS8/Word status changed.


## Structured plan input and wrapper fix — 23 October 2026

- **Y** — Captured the actual failures in the next live diagnostic: malformed JSON embedded in the plan_json string; expected_results supplied as a string instead of a list; source quotes copied with the reader's display line-number prefixes. The evaluation wrapper also parsed the string before canonical validation, bypassing the new typed correction feedback.
- **Y** — Added a preferred native plan object with nested field/array/reference schemas to the existing validate_test_plan tool. Legacy plan_json calls remain supported; exactly one input form is required. The same strict canonical source/identity/size checks apply. Quotes still must match source text; line-number prefixes are not silently stripped or accepted.
- **Y** — The existing evaluation wrapper now uses the canonical bounded decoder and safe typed validation for malformed/sample-scope inputs. Replaying the exact captured malformed input offline confirms useful feedback; the matching native draft is checkable. An unidentifiable malformed original still cannot be silently declared recovered.
- **Y** — Affected compatibility suite: 223 run, 222 passed, one Windows symlink-permission skip, zero failures/errors. All 12 current pilot cases produce identical results through the native and legacy inputs in four bounded batches. Source hashes remain unchanged and every case is still not run.
- **P — BLOCKED** — One changed-path hosted recheck completed its controller in 51.41 seconds (47.56 in the evaluator). OpenRouter reached quota; Groq then failed to connect, before any source read/draft returned. Gemini was not attempted after that connection error under the existing policy. No full live planning pass is claimed and no further hosted attempt followed.
- **Y** — Evaluation failure reporting now distinguishes a failed provider/category from an actual successful model response. An offline mocked connection error verifies that no successful provider is claimed when none returned. The original live record is retained unchanged; read its error/log alongside the corrected reporting behavior.

Code placement stayed in existing agent/tools, agent/runtime, agent/langgraph and evaluations areas; regressions extend existing tests/test_test_plans.py. No new package or dependency was needed. The automation project, provider order/persistent configuration, Jira/Ollama state and WS1-WS8 statuses are unchanged. Stage 9.0 remains Y; 9.1 remains P for design acceptance and a complete live planning flow. No target application or test suite was run.

Evidence: outputs/acceptance/ws9-structured-plan-input-20261023/{affected-offline.json,pilot-input-compatibility.json,wrapper-offline-check.json,failure-report-check.json,live/live.json,before/}. The pre-fix captured input is retained in outputs/acceptance/ws9-bounded-plan-correction-20261023/live-after-correction/live.json. This checkpoint supersedes the earlier statement that the draft-format cause was unknown; its compatibility checks are separate from the outstanding hosted gate. Markdown was updated; the Word diagram remains its earlier snapshot.


## 9.1 selected pilot completion record — 23 October 2026

**Y — complete within the selected Text Input manual-design/pilot scope.** Gemini completed the real read -> validate -> one quote correction -> final answer sequence in 30.55 seconds (36.81 including controller). The original evaluation result was a false negative only because it recognized not run but not this test has not been run. The evaluator now recognizes that equivalent narrative wording and excludes quoted/code-only disclaimers. Four targeted disclosure tests pass; the saved model response was reassessed without a model rerun and its original SHA256 is preserved.

Local answer review confirms source case QPH-001, supplied Hello World data, entry/clear steps, expected outcomes, exact source span and explicit unexecuted status. The original report/log and the reassessment remain separately available. Revision 2 design acceptance is recorded as a delegated decision under the user's choose-the-best instruction; this does not certify an independent human review, all-provider availability, actual application behavior, test execution, or the full WS8 release.

Evidence: outputs/acceptance/ws9-9-1-pilot-completion-20261023/{completion.json,live-reassessment.json,disclosure-tests.json,before/}; original live record: outputs/acceptance/ws9-structured-plan-input-20261023/gemini-isolated/live.json. All 12 cases are still not_run with no actual results. Next is 9.2: scoped observations and defect drafts using real evidence. No target files/commands, persistent provider order/settings, Jira authentication or Ollama requests changed. This update covers Markdown/JSON; the Word diagram remains its earlier snapshot.

## Historical — initial 9.2 observation and defect-draft checkpoint, 23 October 2026

**Component Y; stage acceptance P.** The read-only tool is implemented in the existing tools package, with wrappers/specifications in the existing project, conversation and policy packages. No new flat helper or duplicate provider/action stack was added. The shared backend is available to console/browser orchestration; a live user interface/model acceptance run has not been claimed here.

- **Y** — Read one exact case from either the canonical test_cases pack or the checker's cases output. Require paired steps/expected results and a report bound to the exact case-file SHA256.
- **Y** — Read saved observation notes inside the configured project root, check exact text spans/digests and require actual-result text in the cited note. Outcome/observer identity remain attributed claims, not independently verified behavior.
- **Y** — Keep missing steps not_run with null actual results. Distinguish reported pass, reported failure, blocked and partially observed states. Synthetic reports retain an explicit synthetic status and draft title.
- **Y** — Failed reported steps produce review-only drafts with case/step ID, prerequisites/test data where present, reproduction steps, expected/actual results and evidence. Cause/severity remain undecided; no application run, approval, write, Jira authentication or external issue is performed.
- **Y** — Reject conflicting duplicate steps, wrong IDs, stale revisions, mismatched quotes, self-citation, unknown action/approval fields, invalid timestamps/JSON, unsafe paths, oversized input/output and files changing during review.
- **Y** — Preserve ordinary file-action and explicit Jira routes; local observation analysis does not enter the generic test-case/Jira drafting route.
- **Y** — Offline regressions: 180 tests run, 179 passed, one existing Windows symlink permission skip. Original 12-case pack is unchanged and all cases remain not run. The selected real case-file format was exercised only with clearly synthetic notes.
- **P** — Check actual pilot observations and review a supported defect draft if a failure is observed. No actual observation, application result, reproduced bug or external filing is currently claimed.

### Next user input

For **TI-TC-001**, supply the actual environment/application URL or build, browser, observation time, and these three step results in plain language:

1. Which basic text field was selected and its starting value.
2. Its complete value after entering **Hello World**.
3. Its complete value after clearing the same field.

Include saved observation notes/log text if available. Unknown details stay unknown. You do not need to calculate hashes or hand-author the manifest: after actual notes are supplied, the assistant can prepare a source-linked observation report without inventing results. Application runs and external filing require their own scope. Screenshots can be reviewed separately; this first tool validates saved UTF-8 text evidence and does not claim image inspection.

### Tool contract and sample

`draft_test_observations(case_file, observations_file, case_id)` reads both JSON files within the configured project root and returns a draft; it does not save or execute anything. A report contains schema_version 1, case_pack_sha256, run metadata (id, timezone-aware observed_at, environment, observer, provenance), and up to 20 observations. Each observation identifies case_id, step_number, reported outcome (passed/failed/blocked), actual_result and exact local evidence references (file, start_line, end_line, quote, sha256). Provenance is user_report or synthetic_fixture; a file cannot certify connected-tool execution. Use separate reports for different runs. Underlying requirement references are copied from the case file and explicitly not re-verified by this observation tool.

Evidence and an explicitly synthetic example are in outputs/acceptance/ws9-observations-20261023: tests.json/tests.log, synthetic-notes.txt, synthetic-observations.json, synthetic-result.json and local-acceptance.json. These are fixture results, not test-application results. The exact canonical case pack remains outputs/acceptance/ws9-text-input-pilot-20261023/test-pack.json. Provider order/configuration, Ollama parking, target files and WS1–WS8 statuses are unchanged. Word remains the earlier snapshot.

## Historical — partial user observation intake, 23 October 2026

**9.2 P — actual partial notes received.** The user identified https://qapracticehub.com/#inputs and the Enter your name field, then reported that its placeholder disappears after typing, reappears after clearing, and Backspace removes the selected text. Preserve this as user-reported behavior, not independent agent execution or a complete TI-TC-001 pass. Exact Hello World retention has not been stated; browser and actual observation time are unknown. Receipt/storage time is recorded separately and is not substituted for observation time.

Evidence: outputs/acceptance/ws9-user-observations-20261023/user-notes.txt and partial-intake.json. No failure is reported and no defect draft or external issue is created. The original design pack remains unchanged. This is a partial intake record, not a fabricated complete manifest for the strict observation tool. Next confirmation: was the complete field text exactly Hello World before clearing?

## 9.2 selected observation pilot COMPLETE — 23 October 2026

**Y — TI-TC-001 observation pilot only.** The earlier manual-confirmation loop is superseded by actual isolated Playwright evidence. Windows Computer Use was unavailable, but installed Playwright/Chromium was usable; the earlier inference that this required user confirmation was too narrow. The coding agent inspected the actual page and identified the unique editable ordinary text input from its observed Enter your name placeholder. The first direct-value check passed; screenshot review revealed a cookie banner, so the final accepted check explicitly clicked its observed Decline button, then clicked the field normally before typing. No overlay or protected field was bypassed.

The accepted run observed input values **empty -> Hello World -> empty**, verified placeholder hidden after entry/visible after clearing, and used select-all/Backspace. Chromium 153.0.8010.12, isolated headless viewport 1280x900. Actual observation timestamps and three screenshots are linked to the exact unchanged case-pack hash. The case passed, so no actual defect is claimed or filed. The existing defect-draft failure path was tested offline with clearly synthetic evidence; it does not invent a live failure.

Current execution status is one passed case / 11 not run in outputs/acceptance/ws9-browser-input-20261023/execution-ledger.json. The original 12-case design artifact remains unchanged as a not-run baseline and is not the current execution ledger. Current evidence is entry-clear-with-consent/live-result.json plus initial.png, entered.png and cleared.png. The earlier entry-clear run and partial user intake are preserved separately as history. completion.json records the narrow acceptance scope.

Reusable implementation: agent/tools/browser_inputs.py accepts a selected page, targeting method (exact label/placeholder/role name), field description and required test value; no QA Practice Hub URL, element ID or per-site selector is hardcoded there. It stops for ambiguous/missing/protected/non-text controls and respects click actionability. evaluations/browser_input_acceptance.py is an explicit configurable CLI harness, not an unattended action exposed to the deployed agent. Tests in tests/test_browser_inputs.py plus existing saved-observation regressions: **37 passed** offline. Actual browser capture is not relabelled user_report or synthetic to force it through the saved-report contract.

This proves one reusable text-field capability and one real case. It does not prove every website, email/date/password/dropdown/button behavior, LLM-selected browser plans, automatic agent-chat browser tool use, all browsers, native mobile, target Gradle suites or WS9 release. Those later integrations remain pending. Do not repeat manual exact-value questions for this completed observation. Next planned stage is 9.3; full browser orchestration is 9.4. No target source, persistent provider configuration, Jira/Ollama state or Word snapshot changed.
