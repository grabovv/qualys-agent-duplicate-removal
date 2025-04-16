# Qualys Agent Duplicate Removal

A Python script that connects to the Qualys API, retrieves all registered Cloud Agents, identifies duplicates based on hostname and IP address, and optionally removes them using the Qualys API.

This tool is useful for environments where multiple agents may be installed on the same host or improperly decommissioned, resulting in cluttered asset lists.

---

## 📦 Features

- Fetches Cloud Agents from the Qualys API
- Detects duplicate agents (same hostname and IP)
- Optionally removes duplicates (via API call)
- Includes a `--dry-run` mode for safe simulation
- Generates logs to the `logs/` directory

---

## 🚀 Requirements

- Python 3.12.x or higher
- External packages listed in `requirements.txt`

Install them using:

```
pip install -r requirements.txt
```
---

## ⚙️ Configuration
Before running the script, create a `.env` file in the project root based on the provided `example.env`.<br />
Edit `.env` and fill in your `API_LOGIN`, `API_PASSWORD` and `API_PLATFORM_URL`:

```env
API_LOGIN=your_qualys_username
API_PASSWORD=your_qualys_password
API_PLATFORM_URL=https://qualysapi.qg2.apps.qualys.eu/
API_HEADERS={"X-Requested-With": "Python Requests", "Content-Type": "text/xml"}
API_REQUEST_DELAY=1
```

You can find the appropriate `API_PLATFORM_URL` for your account here:<br />
🔗 [Qualys Platform Identification](https://www.qualys.com/platform-identification/)

---

## 🖥️ Usage
> [!WARNING]
> Before running the script in normal mode, **always start with `--dry-run`**  to verify which agents would be removed.<br />
> This prevents accidental deletions and allows you to validate the script's behavior safely.

🧪 Dry-run mode (no agent deletion performed):
```
python qualys_agent_duplicate_removal.py --dry-run
```


🚨 Normal mode (actual deletion):
```
python qualys_agent_duplicate_removal.py
```

## 📂 Logs
Each run creates a timestamped log file in the logs/ directory, e.g.:
```
logs/CA_REMOVE_2025-04-16_14-30-00.log
```
Logs include details about duplicates found, errors, and removal actions (or dry-run results).

## 🛡️ Disclaimer
> [!CAUTION]
> This tool performs irreversible actions when not run in --dry-run mode. Use with caution.<br />
> It is strongly recommended to run in dry-run mode first and review the logs before proceeding with actual deletions.

## 📄 License
This project is licensed under the MIT License. See the `LICENSE` file for details.

