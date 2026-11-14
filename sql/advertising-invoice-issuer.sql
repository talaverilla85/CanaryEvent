-- Configuración privada del emisor de D’Parranda.
-- Solo persona física (autónomo). El IGIC general 7% se muestra en borradores
-- como desglose orientativo sobre el total (tarifa con IGIC incluido).
-- La aplicación efectiva requiere revisión de régimen y localización del servicio.
-- Aquí no se emiten facturas legales.
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
 igic_general_rate_percent SMALLINT NOT NULL DEFAULT 7 CHECK (igic_general_rate_percent BETWEEN 0 AND 15),
 updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE advertising_invoice_issuer ADD COLUMN IF NOT EXISTS igic_general_rate_percent SMALLINT NOT NULL DEFAULT 7;
UPDATE advertising_invoice_issuer SET igic_general_rate_percent=7 WHERE id=1;
INSERT INTO advertising_invoice_issuer (id,issuer_type)
 VALUES (1,'individual') ON CONFLICT (id) DO NOTHING;
