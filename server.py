import os
import sys
import ssl
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import create_app

if __name__ == '__main__':
    app = create_app()
    
    # Check for SSL certificates
    cert_dir = os.path.join(os.path.dirname(__file__), 'certs')
    cert_file = os.path.join(cert_dir, 'cert.pem')
    key_file = os.path.join(cert_dir, 'key.pem')
    
    ssl_context = None
    if os.path.exists(cert_file) and os.path.exists(key_file):
        with open(cert_file, 'r') as f:
            if 'BEGIN CERTIFICATE' in f.read():
                ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                ssl_context.load_cert_chain(cert_file, key_file)
    
    if ssl_context is None:
        # Use Flask's adhoc SSL
        ssl_context = 'adhoc'
    
    print('')
    print('=' * 60)
    print('  PASSWORDLESS DIGITAL WALLET SERVER')
    print('=' * 60)
    print('')
    print('  Open your browser to:')
    print('')
    print('    https://localhost:5000')
    print('')
    print('  Note: Accept the security warning (self-signed cert)')
    print('')
    print('  Press Ctrl+C to stop the server')
    print('=' * 60)
    print('')
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=True,
        ssl_context=ssl_context
    )
