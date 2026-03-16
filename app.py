"""
Informes de Obra - Backend Flask
"""
from flask import Flask, request, jsonify, send_from_directory
import base64, os, smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

app = Flask(__name__, static_folder='static', static_url_path='')

smtp_cfg = {
    'host':     os.environ.get('SMTP_HOST', 'smtp.gmail.com'),
    'port':     int(os.environ.get('SMTP_PORT', '587')),
    'user':     os.environ.get('SMTP_USER', ''),
    'password': os.environ.get('SMTP_PASS', ''),
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
    return jsonify({'status': 'ok', 'smtp_configured': bool(smtp_cfg['user'] and smtp_cfg['password'])})

@app.route('/api/send-report', methods=['POST', 'OPTIONS'])
def send_report():
    if request.method == 'OPTIONS':
        return jsonify({}), 200

    if not smtp_cfg['user'] or not smtp_cfg['password']:
        return jsonify({'success': False, 'error': 'Servidor de correo no configurado. Contacta al administrador.'}), 400

    # Acepta multipart/form-data (binario) o JSON+base64
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
        msg = MIMEMultipart()
        msg['From'] = f'Informes de Obra <{smtp_cfg["user"]}>'
        msg['To'] = to
        msg['Subject'] = subject
        msg.attach(MIMEText(html_body, 'html'))

        if pdf_bytes:
            part = MIMEBase('application', 'pdf')
            part.set_payload(pdf_bytes)
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f'attachment; filename="{pdf_name}"')
            msg.attach(part)

        with smtplib.SMTP(smtp_cfg['host'], smtp_cfg['port']) as server:
            server.starttls()
            server.login(smtp_cfg['user'], smtp_cfg['password'])
            server.send_message(msg)

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
    print("Informes de Obra - http://localhost:5173")
    app.run(host='0.0.0.0', port=5173, debug=False)
