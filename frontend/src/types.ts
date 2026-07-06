export interface SkuStock {
  id: number
  facility: string
  sku_code: string
  item_type_name: string | null
  inventory_type: string | null
  shelf: string
  quantity: number
  quantity_blocked: number
  quantity_not_found: number
  excess_quantity: number
  net_variance: number
  quantity_damaged: number
  priority: string | null
  section: string | null
  batch_code: string | null
  expiry: string | null
  updated_at: string
}
