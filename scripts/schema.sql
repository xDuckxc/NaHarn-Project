-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create products table
CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    brand TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    stock_quantity INTEGER NOT NULL,
    location_info JSONB NOT NULL,
    embedding vector(1024),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create index for vector similarity search
CREATE INDEX IF NOT EXISTS products_embedding_idx 
ON products USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- Create indexes for filtering
CREATE INDEX IF NOT EXISTS products_category_idx ON products(category);
CREATE INDEX IF NOT EXISTS products_price_idx ON products(price);
CREATE INDEX IF NOT EXISTS products_stock_idx ON products(stock_quantity);

-- Create function for similarity search
CREATE OR REPLACE FUNCTION match_products(
    query_embedding vector(1024),
    match_threshold FLOAT DEFAULT 0.7,
    match_count INT DEFAULT 5
)
RETURNS TABLE (
    id TEXT,
    name TEXT,
    brand TEXT,
    category TEXT,
    description TEXT,
    price DECIMAL,
    stock_quantity INTEGER,
    location_info JSONB,
    similarity FLOAT
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT
        products.id,
        products.name,
        products.brand,
        products.category,
        products.description,
        products.price,
        products.stock_quantity,
        products.location_info,
        1 - (products.embedding <=> query_embedding) AS similarity
    FROM products
    WHERE 1 - (products.embedding <=> query_embedding) > match_threshold
    ORDER BY products.embedding <=> query_embedding
    LIMIT match_count;
END;
$$;
