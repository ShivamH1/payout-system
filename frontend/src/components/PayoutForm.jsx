import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { requestPayout } from '../api/client'

function PayoutForm({ bankAccounts, isLoading }) {
  const [amount, setAmount] = useState('')
  const [bankAccountId, setBankAccountId] = useState('')
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')
  const queryClient = useQueryClient()

  const payoutMutation = useMutation({
    mutationFn: ({ data, key }) => requestPayout(data, key),
    onSuccess: () => {
      setMessage('Payout requested successfully!')
      setError('')
      setAmount('')
      queryClient.invalidateQueries({ queryKey: ['balance'] })
      queryClient.invalidateQueries({ queryKey: ['payouts'] })
    },
    onError: (err) => {
      setError(err.response?.data?.error || 'Failed to request payout')
      setMessage('')
    },
  })

  const handleSubmit = (e) => {
    e.preventDefault()
    setError('')
    setMessage('')

    const amountInRupees = parseFloat(amount)
    if (isNaN(amountInRupees) || amountInRupees <= 0) {
      setError('Please enter a valid amount')
      return
    }

    const amountInPaise = Math.floor(amountInRupees * 100)
    if (!bankAccountId) {
      setError('Please select a bank account')
      return
    }

    const idempotencyKey = crypto.randomUUID()
    payoutMutation.mutate({
      data: {
        amount_paise: amountInPaise,
        bank_account_id: bankAccountId,
      },
      key: idempotencyKey,
    })
  }

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
          <div className="h-10 bg-gray-200 rounded mb-4"></div>
          <div className="h-10 bg-gray-200 rounded mb-4"></div>
          <div className="h-10 bg-gray-200 rounded"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Request Payout</h2>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Amount (₹)
          </label>
          <input
            type="number"
            step="0.01"
            min="0"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
            placeholder="0.00"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Bank Account
          </label>
          <select
            value={bankAccountId}
            onChange={(e) => setBankAccountId(e.target.value)}
            className="block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          >
            <option value="">Select bank account...</option>
            {bankAccounts.map((account) => (
              <option key={account.id} value={account.id}>
                {account.account_holder_name} - {account.ifsc_code}
              </option>
            ))}
          </select>
        </div>
        <button
          type="submit"
          disabled={payoutMutation.isPending}
          className="w-full bg-indigo-600 text-white py-2 px-4 rounded-md hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {payoutMutation.isPending ? 'Processing...' : 'Request Payout'}
        </button>
        {message && (
          <p className="text-green-600 text-sm">{message}</p>
        )}
        {error && (
          <p className="text-red-600 text-sm">{error}</p>
        )}
      </form>
    </div>
  )
}

export default PayoutForm