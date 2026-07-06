import { useEffect, useRef, useState } from "react"
import { supabase } from "@/lib/supabaseClient"
import type { SkuStock } from "@/types"

export function useSkuStock() {
  const [rows, setRows] = useState<Map<number, SkuStock>>(new Map())
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastEventAt, setLastEventAt] = useState<Date | null>(null)
  const rowsRef = useRef(rows)
  rowsRef.current = rows

  useEffect(() => {
    let cancelled = false

    async function loadAll() {
      setLoading(true)
      const pageSize = 1000
      const merged = new Map<number, SkuStock>()
      let from = 0
      // page through in case there are more rows than a single request returns
      while (!cancelled) {
        const { data, error } = await supabase
          .from("sku_stock")
          .select("*")
          .range(from, from + pageSize - 1)
        if (error) {
          setError(error.message)
          break
        }
        for (const row of (data ?? []) as SkuStock[]) {
          merged.set(row.id, row)
        }
        if (!data || data.length < pageSize) break
        from += pageSize
      }
      if (!cancelled) {
        setRows(merged)
        setLoading(false)
      }
    }

    loadAll()

    const channel = supabase
      .channel("sku_stock-changes")
      .on(
        "postgres_changes",
        { event: "*", schema: "public", table: "sku_stock" },
        (payload) => {
          setLastEventAt(new Date())
          setRows((prev) => {
            const next = new Map(prev)
            if (payload.eventType === "DELETE") {
              const oldRow = payload.old as Partial<SkuStock>
              if (oldRow.id != null) next.delete(oldRow.id)
            } else {
              const newRow = payload.new as SkuStock
              next.set(newRow.id, newRow)
            }
            return next
          })
        }
      )
      .subscribe()

    return () => {
      cancelled = true
      supabase.removeChannel(channel)
    }
  }, [])

  return { rows: Array.from(rows.values()), loading, error, lastEventAt }
}
