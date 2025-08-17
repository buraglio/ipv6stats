
# IPv6 Statistics Dashboard
A replit generated IPv6 statistics reporting web service. This was built using replit, modified slightly to run stand alone. 
A Streamlit web application for visualizing global IPv6 adoption metrics, BGP statistics, and historical trends. Automatically fetches data from Cisco 6lab, BGP Stuff, and other public sources.

## Features
- **Real-time IPv6 adoption rates** by country/ASN
- **BGP routing table analytics**
- **Historical trend visualizations** (Plotly charts)
- **Geographic distribution maps** (Folium)
- **Automatic data updates** (daily)

## Prerequisites
- Python ≥ 3.11
- pip ≥ 22.0
- Recommended: Linux server for production

## Installation
```bash
# Clone repository
git clone https://github.com/buraglio/ipv6stats
cd ipv6stats
```

# Create virtual environment
`python -m venv venv`

# Activate environment (Linux/macOS)
`source venv/bin/activate`
# Windows
`.\venv\Scripts\activate`

# Install dependencies
`pip install -e .`

# Usage 

`streamlit run app.py`

# Production deployment

## Option A: Nginx + Gunicorn

### Install production server

`pip install gunicorn`

### Run with 4 workers (adjust as needed)
`gunicorn --bind 0.0.0.0:8501 --workers 4 streamlit.web.bootstrap:run`

### Sample Nginx config (/etc/nginx/sites-available/ipv6-dashboard):

```
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://localhost:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection upgrade;
        proxy_set_header Host $host;
    }
}
```

# Option B: Docker


## This is untested but *should* work. 

### Docker

```
FROM python:3.11
WORKDIR /app
COPY . .
RUN pip install -e .
EXPOSE 8501
CMD [streamlit, run, app.py, --server.port=8501, --server.address=0.0.0.0]
```

### Configuration
Force Light Theme
Create .streamlit/config.toml:

```
[theme]
base = light  # Always use light mode
primaryColor = #4f8bf9  # Optional: Customize colors
Environment Variables
Variable	Purpose
BGP_API_KEY	Auth for BGP data sources
UPDATE_INTERVAL	Data refresh rate (default: 86400s)
```

# Troubleshooting
Python is a bear, and I am terrible at it. I had a lot of issues with versions and the venv. Below are some of the thorns I ran into:

Python version mismatch:

```Bash
pyenv install 3.11.6  # Or use system Python ≥3.11
```

Missing lxml_html_clean:


```Bash
pip install lxml-html-clean  # Note hyphens, not underscores
```

Proxy issues:
- Verify WebSocket headers in Nginx
- Check proxy_set_header Connection "upgrade"

