import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { setMerchantId, getBalance, getLedger, getPayouts, getBankAccounts, requestPayout } from './api/client'
import BalanceCard from './components/BalanceCard'
import PayoutForm from './components/PayoutForm'
import TransactionTable from './components/TransactionTable'
import PayoutHistory from './components/PayoutHistory'

const merchants = [
  { id: '00000000-0000-0000-0000-000000000001', name: 'Acme Agency' },
  { id: '00000000-0000-0000-0000-000000000002', name: 'BuildFast Studio' },
  { id: '00000000-0000-0000-0000-000000000003', name: 'PixelPerfect Labs' },
]

function App() {
  const [selectedMerchant, setSelectedMerchant] = useState('')
  const queryClient = useQueryClient()

  const balanceQuery = useQuery({
    queryKey: ['balance'],
    queryFn: getBalance,
    enabled: !!selectedMerchant,
  })

  const ledgerQuery = useQuery({
    queryKey: ['ledger'],
    queryFn: () => getLedger(1),
    enabled: !!selectedMerchant,
  })

  const payoutsQuery = useQuery({
    queryKey: ['payouts'],
    queryFn: () => getPayouts(1),
    enabled: !!selectedMerchant,
  })

  const bankAccountsQuery = useQuery({
    queryKey: ['bankAccounts'],
    queryFn: getBankAccounts,
    enabled: !!selectedMerchant,
  })

  useEffect(() => {
    if (selectedMerchant) {
      setMerchantId(selectedMerchant)
    }
  }, [selectedMerchant])

  const handleMerchantChange = (e) => {
    const merchantId = e.target.value
    if (merchantId) {
      setMerchantId(merchantId)
    }
    setSelectedMerchant(merchantId)
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-6xl mx-auto py-8 px-4">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900">Company Pay</h1>
          <p className="text-gray-600 mt-1">Payout Dashboard</p>
        </div>

        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Select Merchant
          </label>
          <select
            value={selectedMerchant}
            onChange={handleMerchantChange}
            className="block w-full max-w-md rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm"
          >
            <option value="">Choose a merchant...</option>
            {merchants.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </div>

        {selectedMerchant && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <BalanceCard balance={balanceQuery.data?.data} isLoading={balanceQuery.isLoading} />
              <PayoutForm
                bankAccounts={bankAccountsQuery.data?.data || []}
                isLoading={bankAccountsQuery.isLoading}
              />
            </div>

            <TransactionTable
              entries={ledgerQuery.data?.data?.results || []}
              isLoading={ledgerQuery.isLoading}
            />

            <PayoutHistory
              payouts={payoutsQuery.data?.data?.results || []}
              isLoading={payoutsQuery.isLoading}
            />
          </div>
        )}
      </div>
    </div>
  )
}

export default App