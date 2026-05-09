-- TalkERP – Database Seed Script
-- Executed automatically by docker-compose on first container start.

-- 1. Customer Master (SAP KNA1 equivalent)
CREATE TABLE IF NOT EXISTS customer_master_kna1 (
    customer_id VARCHAR(50) PRIMARY KEY,
    customer_city VARCHAR(100),
    customer_state VARCHAR(2)
);

INSERT INTO customer_master_kna1 (customer_id, customer_city, customer_state) VALUES
('C001', 'Sao Paulo', 'SP'),
('C002', 'Rio de Janeiro', 'RJ'),
('C003', 'Belo Horizonte', 'MG'),
('C004', 'Curitiba', 'PR'),
('C005', 'Porto Alegre', 'RS'),
('C006', 'Salvador', 'BA'),
('C007', 'Fortaleza', 'CE'),
('C008', 'Brasilia', 'DF'),
('C009', 'Campinas', 'SP'),
('C010', 'Manaus', 'AM');

-- 2. Vendor/Seller Master (SAP LFA1 equivalent)
CREATE TABLE IF NOT EXISTS vendor_master_lfa1 (
    seller_id VARCHAR(50) PRIMARY KEY,
    seller_city VARCHAR(100),
    seller_state VARCHAR(2)
);

INSERT INTO vendor_master_lfa1 (seller_id, seller_city, seller_state) VALUES
('V001', 'Sao Paulo', 'SP'),
('V002', 'Franca', 'SP'),
('V003', 'Curitiba', 'PR'),
('V004', 'Rio de Janeiro', 'RJ'),
('V005', 'Joinville', 'SC'),
('V006', 'Belo Horizonte', 'MG'),
('V007', 'Maringa', 'PR'),
('V008', 'Ribeirao Preto', 'SP'),
('V009', 'Florianopolis', 'SC'),
('V010', 'Vitoria', 'ES');

-- 3. Material/Product Master (SAP MARA equivalent)
CREATE TABLE IF NOT EXISTS product_master_mara (
    product_id VARCHAR(50) PRIMARY KEY,
    product_category VARCHAR(100),
    profit_center VARCHAR(20),
    weight_g NUMERIC(10, 2)
);

INSERT INTO product_master_mara (product_id, product_category, profit_center, weight_g) VALUES
('P001', 'health_beauty', 'PC-100', 350.00),
('P002', 'computers_accessories', 'PC-200', 1200.50),
('P003', 'auto', 'PC-300', 5500.00),
('P004', 'bed_bath_table', 'PC-400', 2100.00),
('P005', 'furniture_decor', 'PC-400', 8500.00),
('P006', 'sports_leisure', 'PC-500', 1500.00),
('P007', 'watches_gifts', 'PC-100', 250.00),
('P008', 'telephony', 'PC-200', 400.00),
('P009', 'housewares', 'PC-400', 3200.00),
('P010', 'toys', 'PC-500', 800.00);

-- 4. Sales Document Header (SAP VBAK equivalent)
CREATE TABLE IF NOT EXISTS sales_header_vbak (
    order_id VARCHAR(50) PRIMARY KEY,
    customer_id VARCHAR(50) REFERENCES customer_master_kna1(customer_id),
    order_date TIMESTAMP,
    order_status VARCHAR(20)
);

INSERT INTO sales_header_vbak (order_id, customer_id, order_date, order_status) VALUES
('O1001', 'C001', '2025-11-15 10:30:00', 'delivered'),
('O1002', 'C002', '2025-11-16 14:45:00', 'delivered'),
('O1003', 'C003', '2025-12-01 09:15:00', 'shipped'),
('O1004', 'C004', '2025-12-20 18:20:00', 'delivered'),
('O1005', 'C005', '2026-01-05 11:10:00', 'canceled'),
('O1006', 'C001', '2026-01-15 08:05:00', 'delivered'),
('O1007', 'C006', '2026-02-14 16:50:00', 'delivered'),
('O1008', 'C007', '2026-03-10 13:40:00', 'processing'),
('O1009', 'C008', '2026-04-22 10:25:00', 'delivered'),
('O1010', 'C009', '2026-05-01 19:30:00', 'delivered');

-- 5. Sales Document Item (SAP VBAP equivalent)
CREATE TABLE IF NOT EXISTS sales_item_vbap (
    order_id VARCHAR(50) REFERENCES sales_header_vbak(order_id),
    item_id INT,
    product_id VARCHAR(50) REFERENCES product_master_mara(product_id),
    seller_id VARCHAR(50) REFERENCES vendor_master_lfa1(seller_id),
    price NUMERIC(10, 2),
    freight_value NUMERIC(10, 2),
    cogs NUMERIC(10, 2),
    PRIMARY KEY (order_id, item_id)
);

INSERT INTO sales_item_vbap (order_id, item_id, product_id, seller_id, price, freight_value, cogs) VALUES
('O1001', 1, 'P001', 'V001', 59.90, 15.50, 25.00),
('O1001', 2, 'P007', 'V002', 199.00, 12.00, 110.00),
('O1002', 1, 'P002', 'V003', 850.00, 45.00, 600.00),
('O1003', 1, 'P005', 'V004', 1200.00, 150.00, 950.00),
('O1004', 1, 'P003', 'V005', 450.00, 65.00, 320.00),
('O1005', 1, 'P004', 'V006', 120.00, 25.00, 80.00),
('O1006', 1, 'P008', 'V007', 299.99, 18.50, 150.00),
('O1007', 1, 'P009', 'V008', 89.90, 22.00, 40.00),
('O1008', 1, 'P006', 'V009', 350.00, 30.00, 200.00),
('O1009', 1, 'P010', 'V010', 45.00, 15.00, 15.00),
('O1010', 1, 'P002', 'V003', 820.00, 40.00, 600.00);
