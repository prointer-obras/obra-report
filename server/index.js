import express from 'express'
import nodemailer from 'nodemailer'
import cors from 'cors'
import { readFileSync, existsSync } from 'fs'
import { resolve, join, dirname } from 'path'
import { fileURLToPath } from 'url'

const __dirname = dirname(fileURLToPath(import.meta.url))

// Load .env from project root
const envPath = resolve(__dirname, '../.env')
if (existsSync(envPath)) {
  const envContent = readFileSync(envPath, 'utf8')
  for (const line of envContent.split('\n')) {
    const [key, ...vals] = line.split('=')
    if (key && !key.startsWith('#')) {
      process.env[key.trim()] = vals.join('=').trim()
    }
  }
}

const app = express()
app.use(cors())
app.use(express.json({ limit: '50mb' }))

// In-memory settings store (for demo without .env)
let runtimeSettings = {
  smtpHost: process.env.SMTP_HOST || '',
  smtpPort: process.env.SMTP_PORT || '587',
  smtpUser: process.env.SMTP_USER || '',
  smtpPass: process.env.SMTP_PASS || ''
}

app.get('/api/health', (_req, res) => res.json({ status: 'ok' }))

app.post('/api/settings', (req, res) => {
  runtimeSettings = { ...runtimeSettings, ...req.body }
  res.json({ success: true })
})

app.get('/api/settings', (_req, res) => {
  res.json({
    smtpHost: runtimeSettings.smtpHost,
    smtpPort: runtimeSettings.smtpPort,
    smtpUser: runtimeSettings.smtpUser,
    configured: !!(runtimeSettings.smtpUser && runtimeSettings.smtpPass)
  })
})

app.post('/api/send-report', async (req, res) => {
  const { to, subject, htmlBody, pdfBase64, pdfFilename } = req.body

  if (!runtimeSettings.smtpUser || !runtimeSettings.smtpPass) {
    return res.status(400).json({
      success: false,
      error: 'Servidor de correo no configurado. Ve a Ajustes para configurar el SMTP.'
    })
  }

  try {
    const transporter = nodemailer.createTransport({
      host: runtimeSettings.smtpHost || 'smtp.gmail.com',
      port: parseInt(runtimeSettings.smtpPort || '587'),
      secure: parseInt(runtimeSettings.smtpPort) === 465,
      auth: {
        user: runtimeSettings.smtpUser,
        pass: runtimeSettings.smtpPass
      },
      tls: { rejectUnauthorized: false }
    })

    await transporter.sendMail({
      from: `"Informes de Obra" <${runtimeSettings.smtpUser}>`,
      to,
      subject,
      html: htmlBody,
      attachments: pdfBase64
        ? [{
            filename: pdfFilename || 'informe_semanal.pdf',
            content: pdfBase64,
            encoding: 'base64'
          }]
        : []
    })

    res.json({ success: true, message: `Informe enviado a ${to}` })
  } catch (err) {
    console.error('Email error:', err)
    res.status(500).json({ success: false, error: err.message })
  }
})

// Servir la PWA (carpeta static/)
app.use(express.static(join(__dirname, '../static')))
app.get('*', (_req, res) => res.sendFile(join(__dirname, '../static/index.html')))

const PORT = process.env.PORT || 3001
app.listen(PORT, () => console.log(`🚀 Server on http://localhost:${PORT}`))
