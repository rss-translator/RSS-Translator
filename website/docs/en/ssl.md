The following is only for manual/scripted/docker installations.

It is recommended to use caddy with cloudflare's DNS proxy.


Install Caddy: https://caddyserver.com/docs/install#debian-ubuntu-raspbian

Create caddy configuration file

May refer to [/home/rsstranslator/deploy/Caddyfile](https://github.com/rss-translator/RSS-Translator/blob/main/deploy/Caddyfile)for modification，Normally just change the domain name on the first line

`sudo nano /home/rsstranslator/deploy/Caddyfile`

File Content:
```
example.com {
        encode zstd gzip
        #tls internal
        handle_path /static/* {
                root * /home/rsstranslator/static/
                file_server
        }

        handle_path /media/* {
                root * /home/rsstranslator/media/
                file_server
        }

        reverse_proxy 127.0.0.1:8000
}
```
Once the changes are complete, copy the configuration file to /etc/caddy/Caddyfile and reboot!
```
sudo mv /etc/caddy/Caddyfile /etc/caddy/Caddyfile.back
sudo cp /home/rsstranslator/deploy/Caddyfile /etc/caddy/
sudo systemctl reload caddy
```
If dns proxy is enabled on cloudflare, you need to select Full for encryption mode on the SSL/TLS page of cloudflare.