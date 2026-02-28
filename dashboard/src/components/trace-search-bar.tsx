// Search bar component for trace list — icon + input + clear button

interface Props {
  value: string
  onChange: (value: string) => void
  placeholder?: string
}

export function TraceSearchBar({ value, onChange, placeholder = 'Search by agent name…' }: Props) {
  return (
    <div className="relative flex items-center">
      {/* Search icon */}
      <svg
        className="absolute left-3 w-4 h-4 text-gray-500 pointer-events-none"
        fill="none"
        stroke="currentColor"
        viewBox="0 0 24 24"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          strokeWidth={2}
          d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z"
        />
      </svg>

      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="
          w-full pl-9 pr-8 py-2 text-sm rounded-md
          bg-gray-800 border border-gray-700
          text-gray-200 placeholder-gray-500
          focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500/40
          transition-colors
        "
      />

      {/* Clear button — shown only when there is text */}
      {value && (
        <button
          onClick={() => onChange('')}
          className="absolute right-2 p-0.5 text-gray-500 hover:text-gray-300 transition-colors"
          aria-label="Clear search"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      )}
    </div>
  )
}
