# Google Health API Agent Context

This file defines critical rules, invariants, and guidelines for AI Agents (LLMs) interacting with the `google-health-cli` command-line utility or the `google_health_api` library.

---

## 1. Authentication
* The CLI checks the `GOOGLE_HEALTH_CLI_TOKEN` environment variable first. If set, it will bypass file-based credentials.
* If the environment token is missing, it falls back to reading `token.json` in the current working directory.
* **DO NOT** attempt to trigger interactive `login` in headless environments or CI. It will fail.

---

## 2. Context Window Discipline (Filtering & Masking)
* Google Health API endpoints can return massive datasets.
* **Rule:** You **MUST** append the `--fields` parameter to `list` and `get` operations to limit return payloads to only the fields you need.
* **Example:**
  ```bash
  google-health-cli --fields "dataPoints(steps(count,interval))" steps list
  ```
* **Gotcha:** If you filter out required properties (like `interval` in `steps`), deserialization will fail. Ensure required dataclass properties are included in the fields mask.

---

## 3. Dynamic Introspection (Use `schema`)
* **DO NOT** guess endpoint signatures. If you are unsure of the exact parameters or payload layout, call the `schema` command:
  ```bash
  # List all available endpoints
  google-health-cli schema

  # Introspect a specific operation
  google-health-cli schema heart-rate.create
  ```

---

## 4. Input Hardening & Safety Rules
* The CLI rejects control characters, suspicious characters (`?`, `#`, `%`), and path traversal sequences (`..`) in resource names/IDs.
* **Rule:** If performing mutating operations (create, patch, update, delete), you **MUST** execute them first using the `--dry-run` flag to verify payload correctness:
  ```bash
  google-health-cli --dry-run --json '{"steps": {"count": 500, "interval": {"startTime": "2026-06-26T14:30:00Z", "endTime": "2026-06-26T14:35:00Z"}}}' steps create
  ```

---

## 5. Streaming Results
* For paginated resources, use the `--all` and `--output json` or `--output pretty` flags with caution.
* If streaming large logs or metrics datasets, use `--all` combined with an external parser (like `jq`) to process NDJSON outputs line-by-line.
