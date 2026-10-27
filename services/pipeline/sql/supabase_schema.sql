-- Supabase 대시보드 → SQL Editor 에 붙여넣고 한 번 실행하세요.
-- 테이블 이름을 바꾸려면 ocr_chunks 를 모두 바꾸고 .env 의 COLLECTION 도 같게 맞춥니다.

create extension if not exists vector;

create table if not exists ocr_chunks (
    id         text primary key,
    text       text not null,
    embedding  vector(384) not null,        -- paraphrase-multilingual-MiniLM-L12-v2 차원
    meta       jsonb not null default '{}', -- session, ts, frame_no, chars, source
    created_at timestamptz not null default now()
);

create index if not exists ocr_chunks_embedding_idx
    on ocr_chunks using hnsw (embedding vector_cosine_ops);
create index if not exists ocr_chunks_session_idx
    on ocr_chunks ((meta->>'session'), created_at desc);

-- 서버는 service_role 키로 접근하므로 RLS를 켜 두고 정책은 만들지 않습니다 (anon 키로는 접근 불가).
alter table ocr_chunks enable row level security;

-- 코사인 유사도 top-k 검색 (VectorStore.nearest 에서 호출)
create or replace function match_ocr_chunks(query_embedding vector(384), match_count int default 5)
returns table (id text, text text, meta jsonb, similarity float)
language sql stable
as $$
    select c.id, c.text, c.meta, 1 - (c.embedding <=> query_embedding) as similarity
    from ocr_chunks c
    order by c.embedding <=> query_embedding
    limit match_count;
$$;
