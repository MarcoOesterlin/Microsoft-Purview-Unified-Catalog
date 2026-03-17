# Microsoft Purview Data Quality SQL Expression Validator

A Firefox sidebar extension that validates custom SQL expressions for [Microsoft Purview Unified Catalog data quality rules](https://learn.microsoft.com/en-us/purview/unified-catalog-data-quality-rules#create-a-custom-rule-using-sql-expression) — before you paste them into Purview, so you spot problems instantly without waiting for a rule deployment to fail.

---

## What it does

When you create a custom data quality rule in Microsoft Purview, you write SQL expressions that run against a single dataset. Purview enforces strict constraints on what SQL is allowed — and error messages from Purview itself can be vague. This extension gives you a live validator in your browser sidebar.

As you type, the extension checks your expressions and reports:

| Check | What it catches |
|---|---|
| **Boolean predicate** | Row expressions must evaluate to `true`/`false`. Flags expressions with no comparison, logical operator, or `TRUE`/`FALSE`. |
| **Disallowed DML/DCL** | Blocks `INSERT`, `UPDATE`, `DELETE`, `TRUNCATE`, `DROP`, `ALTER`, `GRANT`, `REVOKE`, `MERGE`. |
| **Unsupported functions** | Flags Purview-specific helpers that are not valid in SQL expressions: `isDelete`, `isError`, `isIgnore`, `isInsert`, `isUpdate`, `isUpsert`, `partitionId`. |
| **JOINs** | SQL rules run against a single table — `JOIN` is not supported. |
| **Window functions** | `ROW_NUMBER()`, `RANK()`, `LAG()`, `LEAD()`, etc. are flagged as **errors** — Purview DQ expressions are row-level predicates; set-based window operations are not supported. |
| **Missing ORDER BY** | `ROW_NUMBER()`, `RANK()`, `DENSE_RANK()` without `ORDER BY` inside `OVER()` produce non-deterministic results and are flagged as errors. |

The validator covers all three expression types that Purview supports:

- **Row expression** *(required)* — evaluated per row to decide if data passes or fails
- **Filter expression** *(optional)* — scopes which rows are included in the quality check
- **Null expression** *(optional)* — defines what counts as a null/missing value

Results update live as you type — no button to click.

---

## Setup in Firefox

### Prerequisites

- [Node.js](https://nodejs.org/) (v18 or newer)
- Firefox (any current version)

### 1. Install and build

```bash
npm install
npm run build
```

This compiles `src/popup.ts` → `dist/popup.js`. You only need to rebuild when you change the TypeScript source.

### 2. Load the extension into Firefox

1. Open Firefox and navigate to:
   ```
   about:debugging#/runtime/this-firefox
   ```
2. Click **Load Temporary Add-on...**
3. Browse to this folder and select **`manifest.json`**
4. The extension is now loaded.

> **Note:** Temporary add-ons are removed when Firefox closes. Repeat step 2–4 each session, or follow the [Firefox permanent installation guide](https://extensionworkshop.com/documentation/develop/temporary-installation-in-firefox/) to sign and install permanently.

### 3. Open the sidebar

- In the Firefox menu bar, click **View → Sidebar → Microsoft Purview Data Quality Validator**
- Or press the keyboard shortcut shown in the Firefox sidebar menu

The validator panel opens on the right side of your browser and stays open while you work.

---

## How to use it

1. Open the sidebar in Firefox (see above).
2. Paste or type your SQL expression into the **Row expression** field.
3. The verdict updates instantly:
   - **Valid** — the expression passes all checks and can be used in Purview.
   - **Warning** — the expression may work but uses patterns (e.g. window functions) that could cause issues.
   - **Invalid** — one or more checks failed. The specific error is listed below the verdict.
4. Optionally fill in the **Filter expression** and **Null expression** fields if your rule uses them.
5. Once the validator shows **Valid**, copy the expression and paste it into the Purview rule editor.

---

## Example expressions for a `Phone` column

**Row expression:**
```sql
Phone RLIKE '^\\+[1-9][0-9]{6,14}$'
```

**Filter expression:**
```sql
Phone IS NOT NULL AND TRIM(Phone) <> ''
```

**Null expression:**
```sql
Phone IS NULL OR TRIM(Phone) IN ('', 'N/A', 'unknown')
```

---

## Development

```bash
npm run build   # compile once
npm run watch   # compile on every save
```

After rebuilding, go to `about:debugging#/runtime/this-firefox`, find the extension, and click **Reload** to pick up changes.

The extension is entirely client-side — no backend, no network calls, no data leaves your browser.

---

## Reference

- [Purview Unified Catalog — Create a custom rule using SQL expression](https://learn.microsoft.com/en-us/purview/unified-catalog-data-quality-rules#create-a-custom-rule-using-sql-expression)
- [Firefox WebExtension sidebar_action API](https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/user_interface/Sidebars)
