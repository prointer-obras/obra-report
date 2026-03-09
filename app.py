"""
Informes de Obra - Backend Flask
"""
from flask import Flask, request, jsonify, send_from_directory
import base64, os, requests as http

app = Flask(__name__, static_folder='static', static_url_path='')

resend_cfg = {
    'api_key': os.environ.get('RESEND_API_KEY', ''),
    'from':    os.environ.get('RESEND_FROM', 'Informes de Obra <onboarding@resend.dev>'),
}

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
    return jsonify({'status': 'ok', 'resend_configured': bool(resend_cfg['api_key'])})

@app.route('/api/send-report', methods=['POST', 'OPTIONS'])
def send_report():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    if not resend_cfg['api_key']:
        return jsonify({'success': False, 'error': 'Falta la variable RESEND_API_KEY en el servidor.'}), 400

    # Acepta multipart/form-data (binario) o JSON+base64 (legacy)
    ct = request.content_type or ''
    if 'multipart/form-data' in ct:
        to        = request.form.get('to', '')
        subject   = request.form.get('subject', 'Informe Semanal')
        html_body = request.form.get('htmlBody', '')
        pdf_file  = request.files.get('pdf')
        pdf_bytes = pdf_file.read() if pdf_file else None
        pdf_name  = pdf_file.filename if pdf_file else 'informe.pdf'
    else:
        data      = request.get_json(force=True)
        to        = data.get('to', '')
        subject   = data.get('subject', 'Informe Semanal')
        html_body = data.get('htmlBody', '')
        pdf_b64   = data.get('pdfBase64', '')
        pdf_bytes = base64.b64decode(pdf_b64) if pdf_b64 else None
        pdf_name  = data.get('pdfFilename', 'informe.pdf')

    try:
        payload = {
            'from':    resend_cfg['from'],
            'to':      [to],
            'subject': subject,
            'html':    html_body,
        }
        if pdf_bytes:
            payload['attachments'] = [{
                'filename': pdf_name,
                'content':  base64.b64encode(pdf_bytes).decode('utf-8'),
            }]

        resp = http.post(
            'https://api.resend.com/emails',
            headers={
                'Authorization': f'Bearer {resend_cfg["api_key"]}',
                'Content-Type':  'application/json',
            },
            json=payload,
            timeout=25,
        )
        resp_data = resp.json()
        if resp.status_code in (200, 201):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': resp_data.get('message', f'Resend error {resp.status_code}')}), 500

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("Informes de Obra - http://localhost:5173")
    app.run(host='0.0.0.0', port=5173, debug=False)
