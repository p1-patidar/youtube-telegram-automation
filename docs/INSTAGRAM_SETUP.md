
## Instagram / Facebook App Configuration

To use the Instagram posting features, you need to configure a Facebook App correctly.

### 1. Create App
1.  Go to [Facebook Developers](https://developers.facebook.com/).
2.  Create a new App (Type: **Business**).

### 2. Basic Settings
1.  Go to **App Settings > Basic**.
2.  **App Domains**: Add `localhost`.
3.  **Privacy Policy URL**: Add any valid URL (e.g., `https://google.com` if testing).
4.  Click **Save Changes**.

### 3. Add Products
1.  Add **Instagram Graph API**.
2.  Add **Facebook Login for Business**.

### 4. Facebook Login Settings
1.  Go to **Facebook Login > Settings**.
2.  **Valid OAuth Redirect URIs**: Add `https://localhost/`.
3.  Click **Save Changes**.

### 5. Get Credentials
1.  Go to **App Settings > Basic**.
2.  Copy **App ID** and **App Secret**.
3.  Paste them into the GUI settings or your `.env` file.

### Common Errors
-   **"Can't load URL"**: You missed adding `localhost` to **App Domains** or `https://localhost/` to **Valid OAuth Redirect URIs**.
-   **"Invalid Scopes"**: Ensure you have added the **Instagram Graph API** product to your app.
