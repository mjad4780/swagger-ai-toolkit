
# Swagger AI Toolkit

**Swagger AI Toolkit** is a set of two simple Python scripts that automate the process of fetching and converting Swagger/OpenAPI documentation into a clean, AI‑ready Markdown format.

## 🧠 The Idea

When you’re working with an API that uses Swagger UI (like `https://petstore.swagger.io/`), you often need to extract the raw OpenAPI specification to feed it into an AI model for code generation. Doing this manually—either by copying the JSON or digging through the page source—is tedious and error‑prone.

**This toolkit solves that problem** by providing two scripts:

1.  **`swagger_fetcher.py`** – automatically downloads the `swagger.json` (OpenAPI) file from any Swagger UI URL.  
2.  **`swagger_to_ai.py`** – converts that JSON into a structured, easy‑to‑read Markdown file.

The final Markdown contains **only** the essential information about your API endpoints: tags, HTTP methods, URLs, headers, request bodies, and success/error responses. It contains **no** cURL commands, no Java, and no Python code samples—just pure, structured API data that AI models like ChatGPT, Claude, and Gemini can understand perfectly.

**Why is this useful?** Because AI models generate much better code (like Flutter/Dart models, Dio clients, or Cubit state management) when you provide them with clear, focused, and concise API documentation. This toolkit gives you exactly that.

## 📦 Installation

### 1. Clone or Download the Repository

```bash
git clone https://github.com/mjad4780/swagger-ai-toolkit.git
cd swagger-ai-toolkit
```

### 2. Install Dependencies

The only required dependency is the `requests` library. Install it using `pip`:

```bash
pip install -r requirements.txt
```

**📌 Important Note about `pip` installation:**  
If you see a message like `Defaulting to user installation because normal site‑packages is not writeable`, **this is not an error**. It simply means that you are not running the command as an administrator or root user, so `pip` is installing the package in your user folder. Your scripts will work perfectly fine. You can safely ignore this message.

## 🚀 How to Use

### Step 1: Fetch the Swagger JSON

Run the fetcher script, providing the URL of your Swagger UI page:

```bash
python swagger_fetcher.py <your_swagger_ui_url>
```

For example, using the public Petstore API:

```bash
python swagger_fetcher.py https://petstore.swagger.io/
```

The script will automatically try common paths (like `/v3/api‑docs`, `/v2/api‑docs`, `/swagger.json`, etc.) and even parse the HTML to find the correct JSON URL. On success, it saves the file as `swagger.json` in the current directory.

**Additional Options:**

- `-o <filename>` – specify a custom output file name (e.g., `-o my_api.json`).  
- `-v` – enable verbose logging to see which URLs are being tried.

### Step 2: Convert to AI‑Ready Markdown

Once you have the `swagger.json` file, run the converter:

```bash
python swagger_to_ai.py swagger.json
```

This will generate a file named `api_for_ai.md` (you can also specify a custom output name with `-o`).

### Step 3: Use the Markdown with an AI

Open the generated `api_for_ai.md` file, copy its entire content, and paste it into your preferred AI tool (ChatGPT, Claude, Gemini) with a prompt like:

> *“Based on this API specification, generate Flutter/Dart models, a Dio HTTP client, a repository pattern implementation, and Cubit state management.”*

## 🔍 Real‑World Example (Petstore)

Let’s walk through a complete example using the public Petstore API:

```bash
# Step 1: Fetch the JSON
python swagger_fetcher.py https://petstore.swagger.io/

# Output:
# swagger.json is saved.

# Step 2: Convert to Markdown
python swagger_to_ai.py swagger.json

# Output:
# api_for_ai.md is created.
```

Now you have a clean, AI‑friendly Markdown file ready to use.

## 🖼️ What the Final Markdown Looks Like

Here’s a short preview of the output you’ll get (formatting may vary slightly). This example shows a typical “Pet” endpoint:

```markdown
# API Documentation for AI

## Pet

### GET /pet/{petId}

**Summary:** Find pet by ID  
**Description:** Returns a single pet.

**Headers:**
- api_key (header, optional): string

**Request Body:**
None

**Success Response:**
Status 200:
- id (required): integer (int64)
- category (required): object
  - id (required): integer (int64)
  - name (required): string
- name (required): string
- photoUrls (required): array of strings
- tags (required): array of objects
  - id (required): integer (int64)
  - name (required): string
- status (required): string (enum: available, pending, sold)

**Error Responses:**
Status Codes: 400, 404, 500

---
```

As you can see, it’s clean, structured, and free of unnecessary clutter—perfect for feeding into an AI.

## 📂 Project Structure

| File | Description |
| :--- | :--- |
| `swagger_fetcher.py` | Fetches `swagger.json` from a Swagger UI URL. |
| `swagger_to_ai.py` | Converts the JSON to an AI‑friendly Markdown file. |
| `requirements.txt` | Lists the project dependencies (only `requests`). |
| `swagger.json` | The downloaded OpenAPI specification (generated in Step 1). |
| `api_for_ai.md` | The final Markdown output (generated in Step 2). |

## ⚠️ Important Notes

- **Circular References (`$ref`):** The converter automatically detects and handles recursive references (e.g., `User -> Order -> User`) to prevent infinite loops and crashes.  
- **If Fetching Fails:** Run the fetcher with the `-v` flag to see detailed logs of which URLs were attempted. Alternatively, open the Swagger UI page in your browser, press `F12` to open Developer Tools, go to the `Network` tab, refresh the page, and look for a request ending in `.json`. Copy that direct URL and use it with the fetcher.  
- **Python Version:** Requires **Python 3.7 or later** due to the use of modern type hints. If you have an older version, please upgrade or remove the type hints from the scripts.  
- **Privacy:** Everything runs locally on your machine. No data is sent to any external server.


## 🤝 Contributing

Contributions are welcome! Feel free to open an issue or submit a pull request.

## 📄 License

This project is licensed under the MIT License.

---

Happy coding! 🚀
```