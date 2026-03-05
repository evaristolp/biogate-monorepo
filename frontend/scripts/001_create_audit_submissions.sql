-- Create audit_submissions table
create table if not exists public.audit_submissions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  email text not null,
  file_name text,
  file_url text,
  status text not null default 'pending' check (status in ('pending', 'processing', 'completed', 'failed')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Enable RLS
alter table public.audit_submissions enable row level security;

-- RLS policies: users can only access their own submissions
create policy "Users can view own submissions"
  on public.audit_submissions for select
  using (auth.uid() = user_id);

create policy "Users can insert own submissions"
  on public.audit_submissions for insert
  with check (auth.uid() = user_id);

create policy "Users can update own submissions"
  on public.audit_submissions for update
  using (auth.uid() = user_id);

-- Create a storage bucket for vendor list uploads
insert into storage.buckets (id, name, public)
values ('vendor-lists', 'vendor-lists', false)
on conflict (id) do nothing;

-- Storage RLS: users can upload to their own folder
create policy "Users can upload vendor lists"
  on storage.objects for insert
  with check (
    bucket_id = 'vendor-lists' and
    (storage.foldername(name))[1] = auth.uid()::text
  );

-- Users can read their own uploads
create policy "Users can read own vendor lists"
  on storage.objects for select
  using (
    bucket_id = 'vendor-lists' and
    (storage.foldername(name))[1] = auth.uid()::text
  );
