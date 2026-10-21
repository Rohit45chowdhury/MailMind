import axios from 'axios'

// Single configured client. The base URL comes only from VITE_API_URL.
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  timeout: 60000,
  headers: { 'Content-Type': 'application/json' },
})

export const API_URL = import.meta.env.VITE_API_URL || '(VITE_API_URL is not set)'

/** Turn any axios/JS error into a message a user can act on. */
export function getErrorMessage(err) {
  if (err?.code === 'ECONNABORTED') return 'The server took too long to respond. Try again in a moment.'
  if (err?.response) {
    const { status, data } = err.response
    const detail = data?.detail
    let text = ''
    if (typeof detail === 'string') text = detail
    else if (Array.isArray(detail)) text = detail.map((d) => `${(d.loc || []).slice(1).join('.') || 'input'}: ${d.msg}`).join('; ')
    else if (data?.message) text = data.message
    if (status === 400 || status === 422) return text ? `Check your input. ${text}` : 'The server rejected this input. Check the fields and try again.'
    if (status >= 500) return `The server hit an error (${status}). ${text || 'Check the backend logs for details.'}`
    return text || `Request failed with status ${status}.`
  }
  if (err?.request) return `Can't reach the backend at ${API_URL}. Make sure FastAPI is running and CORS allows this origin.`
  return err?.message || 'Something went wrong.'
}

async function post(path, payload) {
  const { data } = await api.post(path, payload)
  if (!data || typeof data !== 'object' || Array.isArray(data)) {
    throw new Error('The server returned a response in an unexpected format.')
  }
  return data
}

export const checkSpam = (p) => post('/spam', p)
export const summarizeEmail = (p) => post('/summarize', p)
export const generateEmail = (p) => post('/generate', p)
export const checkGrammar = (p) => post('/grammar-check', p)
export const sendEmail = (p) => post('/send', p)

export default api
