# 🚀 Deploying Finstrat to Streamlit Community Cloud

You are ready to launch! Follow these steps to get **Finstrat** live on the web.

## Phase 1: Push Code to GitHub
Streamlit deploys directly from a GitHub repository.

1.  **Open Terminal (Command Prompt or PowerShell)**
2.  Navigate to your new folder:
    ```powershell
    cd C:\Users\USER\Documents\Finstrat
    ```
3.  Initialize Git and push:
    ```powershell
    git init
    git add .
    git commit -m "Initial commit of Finstrat"
    # Replace the URL below with your actual new GitHub repository URL
    git remote add origin https://github.com/YOUR_USERNAME/finstrat.git
    git branch -M main
    git push -u origin main
    ```
    *(Note: You need to create a new empty repository named `finstrat` on GitHub.com first!)*

## Phase 2: Deploy on Streamlit
1.  Go to [share.streamlit.io](https://share.streamlit.io/).
2.  Log in with your GitHub account.
3.  Click **"New app"**.
4.  Select your **`finstrat`** repository.
5.  Set the **Main file path** to `app.py`.
6.  Click **"Deploy!"**.

## Phase 3: Verify
- Watch the build logs. Streamlit will install everything from `requirements.txt`.
- Once finished, your app will be live at a URL like `https://finstrat.streamlit.app`.

## ⚠️ Important Notes
- **Database**: This app uses a local SQLite database (`stocks.db`). On Streamlit Cloud, this database will **reset** every time the app restarts (which happens frequently).
- **Auto-Updates**: The included GitHub Action (`.github/workflows/update_data.yml`) is designed to fetch new data every hour and commit it back to the repo. This keeps your data fresh even with the database reset!
    - **Action Required**: You need to go to your GitHub Repo Settings -> Actions -> General -> Workflow permissions and select **"Read and write permissions"** for this to work.

## Troubleshooting
- If the app says "No data found", click the **"Refresh Data"** button in the sidebar to trigger an immediate fetch.
