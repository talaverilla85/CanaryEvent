import test from 'node:test';
import assert from 'node:assert/strict';
import {allowedInvoiceEmailRecipient} from '../lib/advertising-invoice-resend.js';
test('sandbox no puede remitir una factura a un cliente real',()=>{
 assert.throws(()=>allowedInvoiceEmailRecipient(true,'cliente@example.org','cliente@example.org','pruebas@example.org'),/Sandbox/);
 assert.equal(allowedInvoiceEmailRecipient(true,'cliente@example.org','pruebas@example.org','pruebas@example.org'),'pruebas@example.org');
});
test('el reenvío real se limita al email fiscal del cliente',()=>{
 assert.equal(allowedInvoiceEmailRecipient(false,'facturas@cliente.es','facturas@cliente.es',''),'facturas@cliente.es');
 assert.throws(()=>allowedInvoiceEmailRecipient(false,'facturas@cliente.es','tercero@cliente.es',''),/correo fiscal/);
});
