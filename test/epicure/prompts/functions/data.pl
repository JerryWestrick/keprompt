% Epicure Gourmet Business Simulation Data
% Facts only - no code

% Clients
client('client_001', 'GOAT NORTE COCINA', 'whats', '+52999123456', 'chef').
client('client_002', 'GOAT NORTE BARRA', 'whats', '+52999654321', 'chef').
client('client_003', 'VILLA MERCEDES', 'email', 'chef@villa.com', 'chef').
client('client_004', 'Casa dela Arugula', 'email', 'info@casaarugula.com', 'chef').

% Products  
product('prod_001', 'Albahaca', 'herbs', 210, 'kg', true).
product('prod_002', 'Arugula', 'herbs', 210, 'kg', true).
product('prod_003', 'Spinach', 'herbs', 180, 'kg', true).
product('prod_004', 'Cilantro', 'herbs', 150, 'kg', true).

% Aliases for fuzzy matching and testing
alias('goat', 'client', 'GOAT NORTE COCINA').
alias('goat', 'client', 'GOAT NORTE BARRA').
alias('villa', 'client', 'VILLA MERCEDES').
alias('arugula', 'client', 'Casa dela Arugula').
alias('arugula', 'product', 'Arugula').
alias('spinach', 'product', 'Spinach').
alias('albahaca', 'product', 'Albahaca').
alias('cilantro', 'product', 'Cilantro').

% Sample orders for testing
order('order_001', 'client_001', '2025-W03', 'confirmed', 'responded').
order('order_002', 'client_002', '2025-W03', 'paid', 'responded').

% Sample order items
order_item('item_001', 'order_001', 'prod_001', 2, 210).
order_item('item_002', 'order_001', 'prod_002', 1, 210).
