# Setup for Secure Local and External API Access

1. Modify your local machine's hosts file:
   - On Windows: Edit `C:\Windows\System32\drivers\etc\hosts`
   - On macOS/Linux: Edit `/etc/hosts`
   - Add this line: `192.168.29.201 dev-api.trademan.ai`

2. Keep your FastAPI server configuration as is:
   ```python
   def main_api():
       uvicorn.run("main:app_fastapi",
                   host="0.0.0.0",
                   port=8081,
                   reload=False,
                   ssl_keyfile='/etc/letsencrypt/live/dev-api.trademan.ai/privkey.pem',
                   ssl_certfile='/etc/letsencrypt/live/dev-api.trademan.ai/fullchain.pem',
                   )
   ```

3. Access your API:
   - Locally: `https://dev-api.trademan.ai:8081`
   - Externally: `https://dev-api.trademan.ai:8081` or `https://115.245.248.122:8081`

4. Update your frontend code:
   - Use `https://dev-api.trademan.ai:8081` as the API endpoint URL
   - This works both locally and externally

5. Ensure your SSL certificate allows for IP SANs:
   - When renewing your Let's Encrypt certificate, include your public IP:
     ```
     certbot certonly --standalone -d dev-api.trademan.ai -d 115.245.248.122
     ```

6. Configure your router/firewall:
   - Forward port 8081 to your server's local IP (192.168.29.201)

7. Regular maintenance:
   - Keep your SSL certificates up-to-date
   - Update your hosts file if your local IP changes