# Test Cases — Update Equipment Operational Status

## Traceability Summary

| Test Case | Category | Acceptance Criterion / Behaviour Covered |
|---|---|---|
| TC-001 | Happy Path | AC1, AC2, AC6 — view an item's current status, save each supported status, and display the persisted result |
| TC-002 | Happy Path | AC3, AC5 — return an item to `Available` and include it for a new reservation when its schedule and quantity permit |
| TC-003 | Negative | AC4 — exclude `Damaged`, `Under Repair`, and `Unavailable` items from new reservation availability and selection without cancelling an existing reservation |
| TC-004 | Negative | AC2, AC6 — reject a status outside the four supported values and preserve the saved status |

### TC-001 — View and Save Each Supported Operational Status

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-001 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that Technical Support Staff can view an equipment item's current operational status and save each supported status. |
| **Pre-conditions** | - Technical Support Staff member `technical.alpha@example.test` is authenticated.<br>- Active catalogue item `EQ-101` exists with name `Portable Projector`, total quantity `4`, and operational status `available`. |
| **Test Steps** | 1. Open the equipment catalogue.<br>2. View `EQ-101` and its current operational status.<br>3. Change the status to `Damaged` and save.<br>4. Refresh or reopen the catalogue item.<br>5. Repeat the save and refresh steps for `Under Repair`, `Unavailable`, and `Available`. |
| **Test Data** | `Equipment ID`: `EQ-101`<br>`Equipment Name`: `Portable Projector`<br>`Statuses`: `Available`, `Damaged`, `Under Repair`, `Unavailable` |
| **Expected Result** | - The initial status is displayed as `Available`.<br>- Each supported status saves successfully.<br>- After every save, the interface displays the selected status.<br>- Refreshing or reopening the item displays the same saved status. |

### TC-002 — Restore Available Equipment to Reservation Eligibility

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-002 |
| **Category** | Happy Path |
| **Test Scenario** | Verify that changing an unavailable item back to `Available` restores eligibility for new reservations while retaining the existing schedule and quantity checks. |
| **Pre-conditions** | - Technical Support Staff member `technical.alpha@example.test` is authenticated.<br>- Active item `EQ-102`, `Wireless Microphone`, has operational status `under_repair`.<br>- Its total quantity, maintenance periods, and reservation schedule allow a new reservation from `3 November 2026, 10:00` to `3 November 2026, 12:00` Singapore time.<br>- The same item has insufficient available quantity for `4 November 2026, 10:00` to `4 November 2026, 12:00` Singapore time because of its saved schedule. |
| **Test Steps** | 1. Search equipment availability for the 3 November period.<br>2. Change `EQ-102` to `Available` and save.<br>3. Repeat the availability search for the 3 November period and select the item for a new reservation.<br>4. Search for the 4 November period. |
| **Test Data** | `Equipment ID`: `EQ-102`<br>`Previous Status`: `Under Repair`<br>`New Status`: `Available`<br>`Eligible Period`: `3 November 2026, 10:00–12:00 SGT`<br>`Schedule-conflict Period`: `4 November 2026, 10:00–12:00 SGT` |
| **Expected Result** | - Before the status change, `EQ-102` is excluded from availability results.<br>- After saving `Available`, it appears for the eligible period and can be selected for a new reservation.<br>- The saved status is displayed as `Available`.<br>- It remains unavailable for the schedule-conflict period; changing the operational status does not bypass schedule or quantity checks. |

### TC-003 — Exclude Non-Available Equipment Without Cancelling Existing Reservations

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-003 |
| **Category** | Negative |
| **Test Scenario** | Verify that every non-available operational status prevents new selection while leaving an existing reservation unchanged. |
| **Pre-conditions** | - Technical Support Staff member `technical.alpha@example.test` is authenticated.<br>- Active items `EQ-103`, `EQ-104`, and `EQ-105` would otherwise have sufficient schedule and quantity availability.<br>- `EQ-103` has an existing saved reservation `RES-501`. |
| **Test Steps** | 1. Save `EQ-103` as `Damaged`, `EQ-104` as `Under Repair`, and `EQ-105` as `Unavailable`.<br>2. Search equipment availability for a new reservation period that would otherwise be eligible.<br>3. Attempt to select each of the three items for a new reservation.<br>4. View existing reservation `RES-501`. |
| **Test Data** | `EQ-103 Status`: `Damaged`<br>`EQ-104 Status`: `Under Repair`<br>`EQ-105 Status`: `Unavailable`<br>`Existing Reservation`: `RES-501` |
| **Expected Result** | - None of the three items appears as available for the new reservation.<br>- None can be selected for the new reservation.<br>- Their saved operational statuses remain visible.<br>- Existing reservation `RES-501` is not automatically cancelled or rewritten. |

### TC-004 — Reject an Unsupported Operational Status

| **Item** | **Content** |
|---|---|
| **Test Case ID** | TC-004 |
| **Category** | Negative |
| **Test Scenario** | Verify that the system accepts only the four approved operational statuses. |
| **Pre-conditions** | - Technical Support Staff member `technical.alpha@example.test` is authenticated.<br>- Equipment item `EQ-106`, `Portable Speaker`, has saved operational status `available`. |
| **Test Steps** | 1. Open `EQ-106`.<br>2. Attempt to save the unsupported operational status `Retired`.<br>3. Refresh or reopen the item. |
| **Test Data** | `Equipment ID`: `EQ-106`<br>`Current Status`: `Available`<br>`Attempted Status`: `Retired` |
| **Expected Result** | - The unsupported status is rejected and is not saved.<br>- The item continues to display `Available` after refresh or reopening.<br>- Its eligibility remains governed by the unchanged `Available` status and the existing schedule and quantity rules. |

## Implementation Dependencies

- The approved behaviour requires a persisted equipment operational status,
  but the documented `equipment` table does not currently contain that field.
- Technical Support currently has documented SELECT access to `equipment` but
  no narrowly scoped operational-status update permission.
- Equipment catalogue, availability, proposal, and final reservation paths
  must consistently enforce the saved operational status after the approved
  database change is deployed.
