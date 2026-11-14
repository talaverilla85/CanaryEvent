-- Configuración privada del emisor de D’Parranda.
-- Solo persona física (autónomo). No se emiten facturas ni se calcula IGIC aquí.
CREATE TABLE IF NOT EXISTS advertising_invoice_issuer (
 id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id=1),
 issuer_type TEXT NOT NULL DEFAULT 'individual' CHECK (issuer_type='individual'),
 legal_name TEXT NOT NULL DEFAULT '',
 tax_id TEXT NOT NULL DEFAULT '',
 billing_address TEXT NOT NULL DEFAULT '',
 billing_postal TEXT NOT NULL DEFAULT '',
 billing_city TEXT NOT NULL DEFAULT '',
 billing_region TEXT NOT NULL DEFAULT '',
 billing_country TEXT NOT NULL DEFAULT 'España',
 copy_email TEXT NOT NULL DEFAULT 'hola@dparranda.es',
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
INSERT INTO advertising_invoice_issuer (id,issuer_type)
 VALUES (1,'individual') ON CONFLICT (id) DO NOTHING;
