import sys
import os

# Add root directory to python path
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Set environment flag for serverless runtime
os.environ.setdefault('NETLIFY', 'true')

from app import app
import serverless_wsgi

def handler(event, context):
    """
    AWS Lambda / Netlify serverless entrypoint for Flask WSGI.
    """
    return serverless_wsgi.handle_request(app, event, context)

if __name__ == '__main__':
    app.run(debug=True)
