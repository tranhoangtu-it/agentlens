// Pagination controls — page size selector, prev/next buttons, page indicator

interface Props {
  total: number
  page: number
  pageSize: number
  onPageChange: (page: number) => void
  onPageSizeChange: (size: number) => void
}

const PAGE_SIZES = [25, 50, 100] as const

export function PaginationControls({ total, page, pageSize, onPageChange, onPageSizeChange }: Props) {
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const start = Math.min((page - 1) * pageSize + 1, total)
  const end = Math.min(page * pageSize, total)

  return (
    <div className="flex flex-wrap items-center justify-between gap-3 mt-4 text-sm text-gray-400">
      {/* Left: showing X–Y of Z */}
      <span className="text-xs">
        {total === 0
          ? 'No results'
          : `Showing ${start}–${end} of ${total.toLocaleString()}`}
      </span>

      {/* Center: prev / page indicator / next */}
      <div className="flex items-center gap-2">
        <button
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="px-3 py-1.5 rounded border border-gray-700 text-xs
                     hover:border-gray-500 hover:text-gray-200 transition-colors
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          ← Prev
        </button>

        <span className="text-xs text-gray-400">
          Page <span className="text-white font-medium">{page}</span> of {totalPages}
        </span>

        <button
          disabled={page >= totalPages}
          onClick={() => onPageChange(page + 1)}
          className="px-3 py-1.5 rounded border border-gray-700 text-xs
                     hover:border-gray-500 hover:text-gray-200 transition-colors
                     disabled:opacity-40 disabled:cursor-not-allowed"
        >
          Next →
        </button>
      </div>

      {/* Right: page size selector */}
      <div className="flex items-center gap-2 text-xs">
        <span className="text-gray-500">Per page</span>
        <select
          value={pageSize}
          onChange={(e) => {
            onPageSizeChange(Number(e.target.value))
            onPageChange(1)
          }}
          className="bg-gray-800 border border-gray-700 text-gray-300 text-xs rounded px-2 py-1
                     focus:outline-none focus:border-blue-500 transition-colors cursor-pointer"
        >
          {PAGE_SIZES.map((s) => (
            <option key={s} value={s}>{s}</option>
          ))}
        </select>
      </div>
    </div>
  )
}
