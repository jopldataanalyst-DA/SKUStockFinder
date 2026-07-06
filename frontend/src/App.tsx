import { Fragment, useMemo, useState } from "react"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { useSkuStock } from "@/hooks/useSkuStock"
import type { SkuStock } from "@/types"

const API_URL = import.meta.env.VITE_API_URL as string

interface SkuGroup {
  key: string
  sku_code: string
  item_type_name: string | null
  facility: string
  totalQuantity: number
  shelves: SkuStock[]
}

function App() {
  const { rows, loading, error, lastEventAt } = useSkuStock()
  const [query, setQuery] = useState("")
  const [refreshing, setRefreshing] = useState(false)
  const [expanded, setExpanded] = useState<Set<string>>(new Set())

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (!q) return rows
    return rows.filter(
      (r) =>
        r.sku_code.toLowerCase().includes(q) ||
        (r.item_type_name ?? "").toLowerCase().includes(q)
    )
  }, [rows, query])

  const grouped = useMemo(() => {
    const groups = new Map<string, SkuGroup>()
    for (const row of filtered) {
      const key = `${row.facility}::${row.sku_code}`
      let group = groups.get(key)
      if (!group) {
        group = {
          key,
          sku_code: row.sku_code,
          item_type_name: row.item_type_name,
          facility: row.facility,
          totalQuantity: 0,
          shelves: [],
        }
        groups.set(key, group)
      }
      group.totalQuantity += row.quantity
      group.shelves.push(row)
    }
    return Array.from(groups.values()).sort((a, b) => a.sku_code.localeCompare(b.sku_code))
  }, [filtered])

  function toggleExpanded(key: string) {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }

  async function triggerRefresh() {
    setRefreshing(true)
    try {
      await fetch(`${API_URL}/refresh`, { method: "POST" })
    } catch {
      // background fetch already retries every 30 min regardless
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div className="flex h-screen w-screen flex-col px-4 py-4">
      <div className="flex items-center justify-between gap-4 mb-4 shrink-0">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">SKU Stock Finder</h1>
          <p className="text-sm text-muted-foreground">
            Live shelfwise inventory · updates automatically every 30 minutes
          </p>
        </div>
        <div className="flex items-center gap-3">
          {lastEventAt && (
            <Badge variant="secondary">
              Live update {lastEventAt.toLocaleTimeString()}
            </Badge>
          )}
          <button
            onClick={triggerRefresh}
            disabled={refreshing}
            className="text-sm rounded-md border px-3 py-1.5 hover:bg-accent disabled:opacity-50"
          >
            {refreshing ? "Refreshing…" : "Refresh now"}
          </button>
        </div>
      </div>

      <Input
        placeholder="Search by SKU code or item name…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        className="mb-4 shrink-0"
      />

      {error && <p className="text-sm text-destructive mb-2 shrink-0">{error}</p>}

      <div className="rounded-md border overflow-auto flex-1 min-h-0">
        <Table>
          <TableHeader className="sticky top-0 bg-background">
            <TableRow>
              <TableHead className="w-6" />
              <TableHead>Item Type</TableHead>
              <TableHead>SKU Code</TableHead>
              <TableHead>Shelves</TableHead>
              <TableHead className="text-right">Total Quantity</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  Loading…
                </TableCell>
              </TableRow>
            ) : grouped.length === 0 ? (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground">
                  No matching SKUs
                </TableCell>
              </TableRow>
            ) : (
              grouped.map((group) => {
                const isOpen = expanded.has(group.key)
                return (
                  <Fragment key={group.key}>
                    <TableRow
                      className="cursor-pointer hover:bg-accent/50"
                      onClick={() => toggleExpanded(group.key)}
                    >
                      <TableCell className="text-muted-foreground">
                        {isOpen ? "▾" : "▸"}
                      </TableCell>
                      <TableCell title={group.item_type_name ?? undefined}>
                        <div className="max-w-[420px] truncate">
                          {group.item_type_name ?? "—"}
                        </div>
                      </TableCell>
                      <TableCell className="font-mono">
                        <div className="max-w-[180px] truncate">{group.sku_code}</div>
                      </TableCell>
                      <TableCell>{group.shelves.length}</TableCell>
                      <TableCell className="text-right font-semibold">
                        {group.totalQuantity}
                      </TableCell>
                    </TableRow>
                    {isOpen &&
                      group.shelves
                        .slice()
                        .sort((a, b) => a.shelf.localeCompare(b.shelf))
                        .map((row) => (
                          <TableRow key={row.id} className="bg-muted/30">
                            <TableCell />
                            <TableCell colSpan={2} className="text-sm text-muted-foreground pl-6">
                              Shelf {row.shelf || "—"}
                            </TableCell>
                            <TableCell />
                            <TableCell className="text-right">{row.quantity}</TableCell>
                          </TableRow>
                        ))}
                  </Fragment>
                )
              })
            )}
          </TableBody>
        </Table>
      </div>

      <p className="text-xs text-muted-foreground mt-3 shrink-0">
        Showing {grouped.length} SKUs ({filtered.length} shelf rows) of {rows.length} total shelf rows
      </p>
    </div>
  )
}

export default App
