How to Add Cloudflare Radar API Token

The code is already configured to use the CLOUDFLARE_API_KEY environment variable. Here are the methods to set it:

Method 1: Set Environment Variable (Recommended)
For current session:
export CLOUDFLARE_API_KEY='your-api-token-here'
streamlit run app.py
For permanent setup (add to your shell profile):
echo 'export CLOUDFLARE_API_KEY="your-api-token-here"' >> ~/.bashrc
source ~/.bashrc

Method 2: Using .env file
Create a .env file in /opt/ipv6stats/:
echo 'CLOUDFLARE_API_KEY=your-api-token-here' > /opt/ipv6stats/.env
Then modify the code to load it using python-dotenv (if not already installed):
pip install python-dotenv

Method 3: Using systemd service file
If you're running this as a systemd service (ipv6stats.service), add the environment variable to the service file:
[Service]
Environment="CLOUDFLARE_API_KEY=your-api-token-here"
Then reload and restart:
sudo systemctl daemon-reload
sudo systemctl restart ipv6stats


How to Get a Cloudflare API Token
Go to https://dash.cloudflare.com/profile/api-tokens
Click "Create Token"
Use the "Read Analytics" template or create a custom token with Zone:Analytics:Read permissions

Copy the generated token
What the API Token Enables
Looking at the code (data_sources.py:458-545), the API token provides:
Live IPv6 traffic data from Cloudflare Radar (52-week timeseries)
Country-specific statistics (data_sources.py:582-646)
Without the token, it falls back to estimated data (~36% IPv6)