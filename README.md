
# Agentic Honey-Pot API (Backend-Only)

This project is a backend-only REST API designed for the "Agentic Honey-Pot for Scam Detection & Intelligence Extraction" hackathon. It receives messages, uses an AI agent powered by the Google Gemini API to engage potential scammers, extracts intelligence, and reports the findings to a final evaluation endpoint.

## How It Works

1.  **Receives Messages:** The API listens for `POST` requests at the `/hcs_A0001` endpoint.
2.  **Authenticates:** It verifies the `x-api-key` header to secure the endpoint.
3.  **Engages AI Agent:** It constructs a detailed prompt and sends the conversation history to the Gemini Pro model. The model is instructed to act as a potential victim to keep the scammer engaged.
4.  **Extracts Intelligence:** The AI agent identifies and extracts key information like UPI IDs, phone numbers, and phishing links from the conversation.
5.  **Manages State:** It keeps track of the conversation history in memory using a session ID.
6.  **Reports Back:** Once the AI agent determines the conversation is complete, it sends a final summary of all extracted intelligence to the required GUVI evaluation endpoint.

---

## Step-by-Step Guide: Setup and Deployment

### Step 1: Local Setup

**Prerequisites:**
*   Python 3.8+
*   pip

**Instructions:**

1.  **Clone the repository and navigate into the directory.**

2.  **Create `.gitignore` file:**
    Create a file named `.gitignore` and add the following content to ensure your secret keys are not committed to GitHub.
    ```
    .env
    venv/
    __pycache__/
    ```

3.  **Create and Configure `.env` file:**
    Copy the example environment file:
    ```bash
    cp .env.example .env
    ```
    Open the newly created `.env` file and replace the placeholder values with your actual secret keys:
    *   `GEMINI_API_KEY`: Your API key from [Google AI Studio](https://aistudio.google.com/app/apikey).
    *   `YOUR_SECRET_API_KEY`: A strong, unique key you create. You will provide this key to the hackathon platform.

4.  **Install Dependencies:**
    It's highly recommended to use a virtual environment.
    ```bash
    # Create a virtual environment
    python -m venv venv

    # Activate it (macOS/Linux)
    source venv/bin/activate
    # Or on Windows: venv\Scripts\activate

    # Install the required packages
    pip install -r requirements.txt
    ```

### Step 2: Test Locally

1.  **Run the Flask Server:**
    With your virtual environment active, start the local server:
    ```bash
    flask run
    ```
    The API will now be running at `http://127.0.0.1:5000`.

2.  **Test with cURL:**
    Open a new terminal and run the following cURL command. Replace `YOUR_SECRET_KEY_HERE` with the key you set in your `.env` file.

    ```bash
    curl -X POST http://127.0.0.1:5000/hcs_A0001 \
    -H "Content-Type: application/json" \
    -H "x-api-key: YOUR_SECRET_KEY_HERE" \
    -d '{
      "sessionId": "local-test-session-123",
      "message": {
        "sender": "scammer",
        "text": "Your bank account will be blocked today. Verify immediately to avoid loss.",
        "timestamp": "2026-01-21T10:15:30Z"
      },
      "conversationHistory": [],
      "metadata": {
        "channel": "SMS",
        "language": "English"
      }
    }'
    ```
    You should receive a JSON response from your AI agent, confirming that the local setup is working.

### Step 3: Deploy to Render (Free Tier)

**Prerequisites:**
*   A GitHub account.
*   A Render account.

**Instructions:**

1.  **Push to GitHub:**
    Initialize a git repository, commit your files (`main.py`, `requirements.txt`, `.gitignore`, `README.md`), and push them to a new GitHub repository. **Verify that your `.env` file is NOT in the repository.**

2.  **Create a New Web Service on Render:**
    *   Log in to your Render dashboard.
    *   Click **New +** and select **Web Service**.
    *   Connect your GitHub account and select the repository you just created.

3.  **Configure the Service:**
    *   **Name:** Give your service a unique name (e.g., `honeypot-api-yourname`).
    *   **Runtime:** Select **Python 3**.
    *   **Build Command:** `pip install -r requirements.txt`
    *   **Start Command:** `gunicorn main:app`
    *   **Instance Type:** Select **Free**.

4.  **Add Environment Variables:**
    *   Go to the **Environment** tab for your new service.
    *   Click **Add Environment Variable** for each key from your local `.env` file. **Do not upload the `.env` file itself.**
    *   **Key:** `GEMINI_API_KEY`, **Value:** `YOUR_ACTUAL_GEMINI_KEY`
    *   **Key:** `YOUR_SECRET_API_KEY`, **Value:** `YOUR_CHOSEN_SECRET_KEY`

5.  **Deploy:**
    *   Click **Create Web Service**.
    *   Render will automatically deploy your application. You can monitor the progress in the **Logs** tab.

### Step 4: Final Submission

Once deployed, Render will provide a public URL (e.g., `https://your-service-name.onrender.com`).

*   **Your API Endpoint URL to submit:** `https://your-service-name.onrender.com/hcs_A0001`
*   **Your API Key to submit:** The value you set for `YOUR_SECRET_API_KEY`.
