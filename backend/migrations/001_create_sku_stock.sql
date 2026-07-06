-- Run this once in the Supabase SQL editor:
-- http://187.127.181.189:8000/project/default/sql/new

create table if not exists public.sku_stock (
  id bigint generated always as identity primary key,
  facility text not null,
  sku_code text not null,
  item_type_name text,
  inventory_type text,
  shelf text not null default '',
  enabled_for_inventory_allocation boolean,
  enabled_for_inventory_sync boolean,
  enabled_for_sku_mixing boolean,
  enabled_for_shelf_hold boolean,
  quantity integer default 0,
  quantity_blocked integer default 0,
  quantity_not_found integer default 0,
  excess_quantity integer default 0,
  net_variance integer default 0,
  quantity_damaged integer default 0,
  priority text,
  section text,
  batch_code text,
  expiry timestamptz,
  updated_at timestamptz not null default now(),
  constraint sku_stock_unique_row unique (facility, sku_code, shelf)
);

create index if not exists sku_stock_sku_code_idx on public.sku_stock using btree (sku_code text_pattern_ops);
create index if not exists sku_stock_item_type_name_idx on public.sku_stock using btree (item_type_name text_pattern_ops);

-- keep updated_at fresh on every upsert
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

drop trigger if exists sku_stock_set_updated_at on public.sku_stock;
create trigger sku_stock_set_updated_at
before update on public.sku_stock
for each row execute function public.set_updated_at();

-- allow anon read access (frontend uses the anon key for search + realtime)
alter table public.sku_stock enable row level security;

drop policy if exists "Allow anon read" on public.sku_stock;
create policy "Allow anon read" on public.sku_stock
  for select
  to anon
  using (true);

-- enable realtime change streaming for this table
alter publication supabase_realtime add table public.sku_stock;
