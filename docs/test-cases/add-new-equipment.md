# Test Cases — Add New Equipment to the Catalogue

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | AC1, AC5: Add a new equipment item with valid details; item is saved as active and appears in the catalogue immediately |
| TC-002 | Boundary | AC2: Total quantity of 1 is accepted |
| TC-003 | Negative | AC3: Saving is blocked with an error when any mandatory field is omitted |
| TC-004 | Negative | AC3: Whitespace-only text fields are treated as omitted |
| TC-005 | Negative / Boundary | AC2, AC4: Saving is blocked with an error when total quantity is 0, negative or not a whole number |
| TC-006 | Happy Path | AC5: Newly saved equipment is visible to an Event Coordinator |
| TC-007 | Happy Path | AC7: An item with a duplicate name is saved as a separate item |
| TC-008 | Negative | AC6: Users without the `technical_support` role cannot add equipment |

### TC-001 — Add Equipment With Valid Details

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify a Technical Support Staff member can add a new equipment item and see it in the active catalogue immediately. |
| **Pre-conditions** | - A user with the `technical_support` role is authenticated.<br>- No catalogue item named `Wireless Lapel Microphone` exists. |
| **Test Steps** | 1. Open the Equipment page.<br>2. Open the add-equipment form.<br>3. Enter the Test Data.<br>4. Submit the form.<br>5. Review the equipment catalogue without logging out or reloading the system. |
| **Test Data** | `Name`: `Wireless Lapel Microphone`<br>`Category`: `Audio`<br>`Description`: `Clip-on wireless microphone with receiver`<br>`Location`: `Main Store, Level 1`<br>`Total quantity`: `8` |
| **Expected Result** | - The item is saved and a success message is displayed.<br>- A new `equipment` record exists with the entered values, `type` = `Audio` and `active` = `true`.<br>- `Wireless Lapel Microphone` appears in the active catalogue immediately with category `Audio` and total quantity `8`. |

### TC-002 — Accept Minimum Valid Quantity

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Boundary |
| **Test Scenario** | Verify a total quantity of 1 is accepted. |
| **Pre-conditions** | - A user with the `technical_support` role is authenticated. |
| **Test Steps** | 1. Open the add-equipment form.<br>2. Enter the Test Data.<br>3. Submit the form. |
| **Test Data** | `Name`: `4K Laser Projector`<br>`Category`: `Visual`<br>`Description`: `High-brightness projector for large halls`<br>`Location`: `Main Store, Level 1`<br>`Total quantity`: `1` |
| **Expected Result** | - The item is saved with total quantity `1`.<br>- The item appears in the active catalogue. |

### TC-003 — Block Saving When a Mandatory Field Is Omitted

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Negative |
| **Test Scenario** | Verify saving is blocked and an error message is displayed when any one mandatory field is left empty. |
| **Pre-conditions** | - A user with the `technical_support` role is authenticated. |
| **Test Steps** | 1. Open the add-equipment form.<br>2. Enter the base valid data from Test Data.<br>3. Clear one field listed in Test Data.<br>4. Submit the form.<br>5. Review the displayed message and the catalogue.<br>6. Repeat steps 1–5 for each listed field. |
| **Test Data** | Base valid data: `Name` `HDMI Switcher`; `Category` `Visual`; `Description` `4-input HDMI switcher`; `Location` `Main Store, Level 2`; `Total quantity` `3`<br>Field cleared per run: `Name`, `Category`, `Description`, `Location`, `Total quantity` |
| **Expected Result** | - For each run, saving is blocked.<br>- An error message identifies the omitted field.<br>- No `equipment` record is created and the catalogue is unchanged. |

### TC-004 — Treat Whitespace-Only Fields as Omitted

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Negative |
| **Test Scenario** | Verify a text field containing only spaces is treated as omitted. |
| **Pre-conditions** | - A user with the `technical_support` role is authenticated. |
| **Test Steps** | 1. Open the add-equipment form.<br>2. Enter the Test Data.<br>3. Submit the form. |
| **Test Data** | `Name`: `"   "` (spaces only)<br>`Category`: `Audio`<br>`Description`: `Portable PA speaker`<br>`Location`: `Main Store, Level 1`<br>`Total quantity`: `2` |
| **Expected Result** | - Saving is blocked.<br>- An error message indicates that the name is required.<br>- No `equipment` record is created. |

### TC-005 — Block Saving When Total Quantity Is Invalid

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-005 |
| **Category** | Negative / Boundary |
| **Test Scenario** | Verify saving is blocked and an error message is displayed when total quantity is 0, negative or not a whole number. |
| **Pre-conditions** | - A user with the `technical_support` role is authenticated. |
| **Test Steps** | 1. Open the add-equipment form.<br>2. Enter the base valid data with one invalid quantity from Test Data.<br>3. Submit the form.<br>4. Review the displayed message and the catalogue.<br>5. Repeat for each invalid quantity. |
| **Test Data** | Base valid data: `Name` `Portable Speaker`; `Category` `Audio`; `Description` `Battery-powered speaker`; `Location` `Main Store, Level 1`<br>Invalid quantities per run: `0`, `-1`, `2.5`, `abc` |
| **Expected Result** | - For each run, saving is blocked.<br>- An error message states that total quantity must be a whole number greater than 0.<br>- No `equipment` record is created and the catalogue is unchanged. |

### TC-006 — New Equipment Is Visible to Event Coordinators

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-006 |
| **Category** | Happy Path |
| **Test Scenario** | Verify newly saved equipment is available to Event Coordinators for future event selection. |
| **Pre-conditions** | - `Wireless Lapel Microphone` was added in TC-001.<br>- A user with the `event_coordinator` role is authenticated. |
| **Test Steps** | 1. As the Event Coordinator, open the equipment list used for event equipment requests.<br>2. Look for the newly added item. |
| **Test Data** | `Equipment`: `Wireless Lapel Microphone` |
| **Expected Result** | - `Wireless Lapel Microphone` is listed with category `Audio` and total quantity `8`. |

### TC-007 — Save Equipment With a Duplicate Name

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-007 |
| **Category** | Happy Path |
| **Test Scenario** | Verify an item whose name matches an existing catalogue item is saved as a separate item. |
| **Pre-conditions** | - A user with the `technical_support` role is authenticated.<br>- `Wireless Lapel Microphone` already exists in the catalogue. |
| **Test Steps** | 1. Open the add-equipment form.<br>2. Enter the Test Data.<br>3. Submit the form.<br>4. Review the catalogue. |
| **Test Data** | `Name`: `Wireless Lapel Microphone`<br>`Category`: `Audio`<br>`Description`: `Second batch purchased for East Wing`<br>`Location`: `East Wing Store`<br>`Total quantity`: `4` |
| **Expected Result** | - The item is saved successfully.<br>- The catalogue shows two separate `Wireless Lapel Microphone` items, each with its own location and quantity.<br>- The existing item's quantity is unchanged. |

### TC-008 — Reject Equipment Creation by Unauthorised Users

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-008 |
| **Category** | Negative |
| **Test Scenario** | Verify users without the `technical_support` role cannot add equipment. |
| **Pre-conditions** | - Users exist with the roles listed in Test Data, none of whom hold `technical_support`. |
| **Test Steps** | 1. Authenticate as each user in Test Data, or send the request without authentication.<br>2. Submit a valid equipment creation request.<br>3. Review the response and the catalogue. |
| **Test Data** | Roles per run: `event_coordinator`, `event_organiser`, `venue_staff`, `attendee`, unauthenticated<br>Equipment: `Name` `Stage Monitor`; `Category` `Audio`; `Description` `Floor wedge monitor`; `Location` `Main Store, Level 1`; `Total quantity` `2` |
| **Expected Result** | - Each request is rejected with an authorisation error.<br>- No `equipment` record is created. |