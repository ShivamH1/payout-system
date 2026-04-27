function formatPaiseToRupees(paise) {
  return `₹${(paise / 100).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
}

function BalanceCard({ balance, isLoading }) {
  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow p-6">
        <div className="animate-pulse">
          <div className="h-4 bg-gray-200 rounded w-1/2 mb-4"></div>
          <div className="h-8 bg-gray-200 rounded w-3/4"></div>
        </div>
      </div>
    )
  }

  if (!balance) {
    return null
  }

  return (
    <div className="bg-white rounded-lg shadow p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Balance</h2>
      <dl className="space-y-3">
        <div className="flex justify-between">
          <dt className="text-gray-600">Available Balance</dt>
          <dd className="text-xl font-bold text-green-600">
            {formatPaiseToRupees(balance.available_paise)}
          </dd>
        </div>
        <div className="flex justify-between">
          <dt className="text-gray-600">Held (in transit)</dt>
          <dd className="text-lg font-medium text-yellow-600">
            {formatPaiseToRupees(balance.held_paise)}
          </dd>
        </div>
        <div className="flex justify-between border-t pt-3">
          <dt className="text-gray-600">Total</dt>
          <dd className="text-lg font-semibold text-gray-900">
            {formatPaiseToRupees(balance.total_paise)}
          </dd>
        </div>
      </dl>
    </div>
  )
}

export default BalanceCard