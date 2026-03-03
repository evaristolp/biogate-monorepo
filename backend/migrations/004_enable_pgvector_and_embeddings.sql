-- Enable pgvector for future embedding-based risk scoring.
-- Safe to run multiple times; uses IF NOT EXISTS.

create extension if not exists vector;

-- Optional: table to store vendor embeddings for similarity search.
-- This prepares for Week 4 composite risk work without changing
-- the existing audits/vendors schema.

create table if not exists vendor_embeddings (
    vendor_id uuid primary key references vendors(id) on delete cascade,
    embedding vector(1536), -- adjust dimension when model is chosen
    created_at timestamptz not null default now()
);

create index if not exists idx_vendor_embeddings_embedding
    on vendor_embeddings
    using ivfflat (embedding vector_cosine_ops)
    with (lists = 100);

