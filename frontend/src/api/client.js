import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
})

export const setMerchantId = (id) => {
  api.defaults.headers.common['X-Merchant-ID'] = id
}

export const getBalance = () => api.get('/api/v1/balance/')
export const getLedger = (page = 1) => api.get(`/api/v1/ledger/?page=${page}`)
export const getPayouts = (page = 1) => api.get(`/api/v1/payouts/?page=${page}`)
export const getBankAccounts = () => api.get('/api/v1/bank-accounts/')
export const requestPayout = (data, idempotencyKey) =>
  api.post('/api/v1/payouts/', data, {
    headers: { 'Idempotency-Key': idempotencyKey },
  })

export default api