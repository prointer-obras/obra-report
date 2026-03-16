"""
Informes de Obra - Backend Flask
"""
from flask import Flask, request, jsonify, send_from_directory
import base64, os, requests as req

app = Flask(__name__, static_folder='static', static_url_path='')

BREVO_API_KEY  = os.environ.get('BREVO_API_KEY', '')
FROM_EMAIL     = os.environ.get('FROM_EMAIL', 'obrareport@gmail.com')
FROM_NAME      = os.environ.get('FROM_NAME', 'Informes de Obra')

def cors(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@app.after_request
def add_cors(r): return cors(r)

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def static_files(path):
    if path and not path.startswith('api/'):
        return send_from_directory('static', path)
    return send_from_directory('static', 'index.html')

@app.route('/api/health')
def health():
    return jsonify({'status': 'ok', 'brevo_configured': bool(BREVO_API_KEY)})

@app.route('/api/send-report', methods=['POST', 'OPTIONS'])
def send_report():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    if not BREVO_API_KEY:
        return jsonify({'success': False, 'error': 'Clave Brevo no configurada. Contacta al administrador.'}), 400

    try:
        ct = request.content_type or ''
        if 'multipart/form-data' in ct:
            to        = request.form.get('to', '')
            subject   = request.form.get('subject', 'Informe Semanal')
            html_body = request.form.get('htmlBody', '')
            pdf_file  = request.files.get('pdf')
            pdf_bytes = pdf_file.read() if pdf_file else None
            pdf_name  = pdf_file.filename if pdf_file else 'informe.pdf'
        else:
            data      = request.get_json(force=True) or {}
            to        = data.get('to', '')
            subject   = data.get('subject', 'Informe Semanal')
            html_body = data.get('htmlBody', '')
            pdf_b64   = data.get('pdfBase64', '')
            pdf_bytes = base64.b64decode(pdf_b64) if pdf_b64 else None
            pdf_name  = data.get('pdfFilename', 'informe.pdf')
    except Exception as e:
        return jsonify({'success': False, 'error': 'Error leyendo petición: ' + str(e)}), 400

    try:
        payload = {
            'sender':      {'name': FROM_NAME, 'email': FROM_EMAIL},
            'to':          [{'email': to}],
            'subject':     subject,
            'htmlContent': html_body,
        }
        if pdf_bytes:
            payload['attachment'] = [{
                'name':    pdf_name,
                'content': base64.b64encode(pdf_bytes).decode('utf-8'),
            }]

        resp = req.post(
            'https://api.brevo.com/v3/smtp/email',
            headers={
                'api-key':      BREVO_API_KEY,
                'Content-Type': 'application/json',
            },
            json=payload,
            timeout=30,
        )

        if resp.status_code in (200, 201):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': f'Error Brevo {resp.status_code}: {resp.text}'}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("Informes de Obra - http://localhost:5173")
    app.run(host='0.0.0.0', port=5173, debug=False)
