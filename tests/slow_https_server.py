"""
To test slow connection behavior:

1. Run this server (HTTPS default):
       python tests/slow_https_server.py
   
   OR Run in plain HTTP mode:
       python tests/slow_https_server.py --http

2. In Wingosy settings, set host to:
       https://127.0.0.1:8443 (for HTTPS)
       http://127.0.0.1:8080 (for HTTP)

3. Launch Wingosy and observe:
   - Does the UI freeze or stay responsive?
   - Does the false "failed to connect" banner appear?
   - Does the app eventually connect after the delay?
   - Check ~/.wingosy/app.log for timeout errors
"""

import http.server
import ssl
import time
import json
import socket
import datetime
import ipaddress
import argparse
import sys
from pathlib import Path

# Generate self-signed certificate using cryptography
def generate_self_signed_cert(cert_file, key_file):
    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
    except ImportError:
        print("Error: 'cryptography' package is required for HTTPS mode.")
        print("Install it with: pip install cryptography")
        sys.exit(1)

    key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    with open(key_file, "wb") as f:
        f.write(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    subject = issuer = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, u"US"),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"CA"),
        x509.NameAttribute(NameOID.LOCALITY_NAME, u"San Francisco"),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"Wingosy Test"),
        x509.NameAttribute(NameOID.COMMON_NAME, u"127.0.0.1"),
    ])
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        issuer
    ).public_key(
        key.public_key()
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.datetime.utcnow()
    ).not_valid_after(
        datetime.datetime.utcnow() + datetime.timedelta(days=10)
    ).add_extension(
        x509.SubjectAlternativeName([
            x509.DNSName(u"localhost"), 
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1"))
        ]),
        critical=False,
    ).sign(key, hashes.SHA256())

    with open(cert_file, "wb") as f:
        f.write(cert.public_bytes(serialization.Encoding.PEM))

class SlowRomMHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        print(f"[{datetime.datetime.now()}] GET {self.path} received")
        
        if self.path == "/api/heartbeat":
            # Respond immediately to heartbeat
            self.send_response(404)
            self.end_headers()
            print(f"[{datetime.datetime.now()}] 404 sent for {self.path} (immediate)")
        elif self.path.startswith("/api/roms"):
            delay = 210
            print(f"[{datetime.datetime.now()}] Simulating {delay}s delay...")
            time.sleep(delay)
            
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"items": [], "total": 0}
            self.wfile.write(json.dumps(response).encode("utf-8"))
            print(f"[{datetime.datetime.now()}] Response sent for {self.path}")
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        print(f"[{datetime.datetime.now()}] POST {self.path} received")
        
        if self.path == "/api/token":
            # Respond immediately to token requests
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            response = {"access_token": "test_token", "token_type": "bearer"}
            self.wfile.write(json.dumps(response).encode("utf-8"))
            print(f"[{datetime.datetime.now()}] Response sent for {self.path} (immediate)")
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    parser = argparse.ArgumentParser(description="Slow RomM Test Server")
    parser.add_argument("--http", action="store_true", help="Run in plain HTTP mode (no SSL)")
    args = parser.parse_args()

    if args.http:
        port = 8080
        server_address = ('127.0.0.1', port)
        httpd = http.server.HTTPServer(server_address, SlowRomMHandler)
        print(f"[{datetime.datetime.now()}] Starting slow HTTP RomM server on http://127.0.0.1:{port}")
    else:
        port = 8443
        cert_file = "test_cert.pem"
        key_file = "test_key.pem"
        
        if not Path(cert_file).exists() or not Path(key_file).exists():
            print("Generating self-signed certificate...")
            generate_self_signed_cert(cert_file, key_file)

        server_address = ('127.0.0.1', port)
        httpd = http.server.HTTPServer(server_address, SlowRomMHandler)
        
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certfile=cert_file, keyfile=key_file)
        httpd.socket = context.wrap_socket(httpd.socket, server_side=True)
        print(f"[{datetime.datetime.now()}] Starting slow HTTPS RomM server on https://127.0.0.1:{port}")

    print("Press Ctrl+C to stop.")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server.")
        httpd.server_close()

if __name__ == "__main__":
    run_server()
