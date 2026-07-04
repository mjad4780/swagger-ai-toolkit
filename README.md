
```markdown
# Swagger AI Toolkit

**Swagger AI Toolkit** is a set of two Python scripts that automate fetching and converting Swagger/OpenAPI documentation into clean, AI‑ready Markdown.

---

## 🧠 The Idea

When you work with an API that uses Swagger UI (e.g., `https://your-api.com/swagger-ui/index.html`), you often need to extract the raw OpenAPI specification to feed into an AI model for code generation. Doing this manually is tedious.

**This toolkit solves that** by providing two scripts:

1. **`swagger_fetcher.py`** – automatically downloads the `swagger.json` (OpenAPI) file from any Swagger UI URL.  
2. **`swagger_to_ai.py`** – converts that JSON into structured Markdown.

The output contains **only** essential endpoint information: tags, methods, URLs, headers, request bodies, and success/error responses.  
**No** cURL, Java, Python, or JavaScript samples—just pure API structure that AI models like ChatGPT, Claude, and Gemini can understand perfectly.

---

## 📦 Installation

### 1. Clone or Download

```bash
git clone https://github.com/mjad4780/swagger-ai-toolkit.git
cd swagger-ai-toolkit
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

> **📌 Note about `Defaulting to user installation`:**  
> If you see this message, it’s **not an error**. It simply means you’re not running as administrator, so `pip` installs packages in your user folder. Your scripts will work fine.

---

## 🚀 How to Use

### Step 1: Fetch the Swagger JSON

Run the fetcher with **your own Swagger UI URL** (replace the placeholder):

```bash
python swagger_fetcher.py https://your-api-domain.com/swagger-ui/index.html
```

The script tries common paths (`/v3/api-docs`, `/v2/api-docs`, `/swagger.json`, etc.) and even parses the HTML to locate the JSON.

**Options:**
- `-o <filename>` – custom output file (default: `swagger.json`).
- `-v` – verbose logging to see what URLs are attempted.

### Step 2: Convert to AI‑Ready Markdown

Now convert the JSON into Markdown:

```bash
python swagger_to_ai.py swagger.json
```

**By default**, this creates a folder named `api_docs/` containing **separate Markdown files for each API tag** (e.g., `auth.md`, `profile.md`, `orders.md`) plus an index file (`README.md`).  
If you prefer a **single file** (legacy mode), use the `--single` flag:

```bash
python swagger_to_ai.py swagger.json --single -o api_for_ai.md
```

**Options:**
- `--output-dir <dir>` – change the output folder (default: `api_docs`).
- `--single` – generate one single file instead of splitting by tag.
- `-o <file>` – specify output filename (only valid with `--single`).
- `--verbose` – show detailed logs.

---

## 🖼️ What the Final Markdown Looks Like (Sample Output)

Below is a shortened preview of what you’ll see in one of the generated files:

```markdown
# Auth API Endpoints

### POST /api/auth/login

**Summary:** User login  
**Description:** Authenticates a user and returns a token.

**Headers:**
- X-API-Key (header, required): string

**Request Body:**
- email (required): string
- password (required): string

**Success Response:**
Status 200:
- token (required): string
- user (required): object
  - id (required): integer
  - name (required): string
  - email (required): string

**Error Responses:**
Status Codes: 400, 401, 500

---
```

No extra noise—just the API structure your AI needs.

---

## 📂 Project Structure

| File / Folder | Description |
| :--- | :--- |
| `swagger_fetcher.py` | Fetches `swagger.json` from a Swagger UI URL. |
| `swagger_to_ai.py` | Converts JSON to Markdown (split by tag by default). |
| `requirements.txt` | Only dependency: `requests`. |
| `swagger.json` | Downloaded OpenAPI spec (generated in Step 1). |
| `api_docs/` | Output folder (generated in Step 2) with per‑tag `.md` files and an index. |

---

## ⚠️ Important Notes

- **Circular References (`$ref`):** The converter automatically detects and stops recursive references (`User -> Order -> User`) to prevent crashes.
- **If Fetching Fails:** Use `-v` to see which URLs are tried. Alternatively, open the Swagger UI, press `F12` → `Network`, refresh, and look for a `.json` request. Copy that direct URL and pass it to the fetcher.
- **Python Version:** Requires **Python 3.7+** due to modern type hints. Upgrade if needed.
- **Privacy:** Everything runs locally—no data is sent anywhere.

---

## 🤝 Contributing

Contributions are welcome! Feel free to open issues or pull requests.

## 📄 License

MIT – free to use, modify, and distribute.

---

Happy coding! 🚀
```

---
