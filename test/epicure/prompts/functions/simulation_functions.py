"""
Epicure Expert System Function Definitions
Contains the FUNCTIONS data structure with Prolog Variable Binding System (_pNN parameters)
"""

# Function definitions with Prolog Variable Binding System (_pNN parameters)
FUNCTIONS = [
    # Universal Query Functions - Core Wabadapa Innovation
    {
        "name": "get_clients",
        "description": "Universal Query: Show clients with optional filtering - Use any combination of parameters",
        "parameters": {
            "type": "object",
            "properties": {
                "id_p01": {"type": "string", "description": "Client ID (omit for all clients)"},
                "name_p02": {"type": "string", "description": "Client name (omit for all clients)"},
                "contact_type_p03": {"type": "string", "description": "Contact method (omit for all types)"},
                "contact_info_p04": {"type": "string", "description": "Contact info (omit for all)"},
                "client_type_p05": {"type": "string", "description": "Client type (omit for all types)"}
            },
            "required": []
        }
    },
    {
        "name": "get_products",
        "description": "Universal Query: Show products with optional filtering - Use any combination of parameters",
        "parameters": {
            "type": "object",
            "properties": {
                "id_p01": {"type": "string", "description": "Product ID (omit for all products)"},
                "name_p02": {"type": "string", "description": "Product name (omit for all products)"},
                "category_p03": {"type": "string", "description": "Product category (omit for all categories)"},
                "unit_price_p04": {"type": "number", "description": "Unit price (omit for all prices)"},
                "unit_p05": {"type": "string", "description": "Unit of measurement (omit for all units)"},
                "available_p06": {"type": "boolean", "description": "Availability status (omit for all)"}
            },
            "required": []
        }
    },
    {
        "name": "get_orders",
        "description": "Universal Query: Show orders with optional filtering - Use any combination of parameters",
        "parameters": {
            "type": "object",
            "properties": {
                "id_p01": {"type": "string", "description": "Order ID (omit for all orders)"},
                "client_id_p02": {"type": "string", "description": "Client ID (omit for all clients)"},
                "week_p03": {"type": "string", "description": "Week identifier (omit for all weeks)"},
                "order_status_p04": {"type": "string", "description": "Order status (omit for all statuses)"},
                "response_status_p05": {"type": "string", "description": "Response status (omit for all)"}
            },
            "required": []
        }
    },
    
    # BusinessEvents with _pNN parameters
    {
        "name": "record_payment",
        "description": "BusinessEvent: Client pays a bill - Record when a client makes a payment for their order",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name_p01": {"type": "string", "description": "Name of the client making payment (supports fuzzy matching like 'Goat' for GOAT restaurants)"},
                "amount_p02": {"type": "number", "description": "Payment amount in dollars"},
                "payment_method_p03": {"type": "string", "description": "How the client paid (cash, transfer, etc.)", "enum": ["cash", "transfer", "card", "check", "other"]}
            },
            "required": ["client_name_p01", "amount_p02"]
        }
    },
    {
        "name": "create_order",
        "description": "BusinessEvent: Client places an order - Create a new weekly order for a client",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name_p01": {"type": "string", "description": "Name of the client placing the order (supports fuzzy matching)"},
                "week_p02": {"type": "string", "description": "Week identifier for the order (e.g., '2025-W25')"}
            },
            "required": ["client_name_p01", "week_p02"]
        }
    },
    {
        "name": "add_order_item",
        "description": "BusinessEvent: Add product to an order - Add a specific product with quantity to an existing order",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id_p01": {"type": "string", "description": "ID of the order to add items to"},
                "product_name_p02": {"type": "string", "description": "Name of the product to add (supports fuzzy matching like 'albahaca' for herbs)"},
                "quantity_p03": {"type": "number", "description": "Quantity of the product to order"},
                "unit_price_p04": {"type": "number", "description": "Override price per unit (optional - uses default product price if not specified)"}
            },
            "required": ["order_id_p01", "product_name_p02", "quantity_p03"]
        }
    },
    {
        "name": "start_new_week",
        "description": "BusinessEvent: Begin a new weekly order cycle - Create initial orders for all active clients for a new week",
        "parameters": {
            "type": "object",
            "properties": {
                "week_date_p01": {"type": "string", "description": "Delivery date for the week (Thursday date when products are delivered)"}
            },
            "required": ["week_date_p01"]
        }
    },
    {
        "name": "mark_client_responded",
        "description": "BusinessEvent: Client has responded to order request - Track whether clients have confirmed, declined, or responded to weekly order requests",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name_p01": {"type": "string", "description": "Name of the client who responded (supports fuzzy matching)"},
                "week_p02": {"type": "string", "description": "Week identifier for the response"},
                "response_p03": {"type": "string", "description": "Type of response from the client", "enum": ["confirmed", "declined", "responded"]}
            },
            "required": ["client_name_p01", "week_p02", "response_p03"]
        }
    },
    {
        "name": "create_client",
        "description": "BusinessEvent: Add a new client to the system - Create a new client record",
        "parameters": {
            "type": "object",
            "properties": {
                "name_p01": {"type": "string", "description": "Client name"},
                "contact_type_p02": {"type": "string", "description": "Contact method (whats, email, tel)", "enum": ["whats", "email", "tel"]},
                "contact_info_p03": {"type": "string", "description": "Contact information (phone, email, etc.)"},
                "client_type_p04": {"type": "string", "description": "Type of client (chef, individual, etc.)", "enum": ["chef", "individual"]}
            },
            "required": ["name_p01", "contact_info_p03"]
        }
    },
    {
        "name": "update_client",
        "description": "BusinessEvent: Update client information - Modify existing client details",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name_p01": {"type": "string", "description": "Name of the client to update (supports fuzzy matching)"},
                "name_p02": {"type": "string", "description": "New client name (optional)"},
                "contact_type_p03": {"type": "string", "description": "New contact method (optional)", "enum": ["whats", "email", "tel"]},
                "contact_info_p04": {"type": "string", "description": "New contact information (optional)"},
                "client_type_p05": {"type": "string", "description": "New client type (optional)", "enum": ["chef", "individual"]}
            },
            "required": ["client_name_p01"]
        }
    },
    {
        "name": "create_product",
        "description": "BusinessEvent: Add a new product to the system - Create a new product record",
        "parameters": {
            "type": "object",
            "properties": {
                "name_p01": {"type": "string", "description": "Product name"},
                "category_p02": {"type": "string", "description": "Product category", "enum": ["herbs", "vegetables", "fruits", "other"]},
                "unit_price_p03": {"type": "number", "description": "Price per unit"},
                "unit_p04": {"type": "string", "description": "Unit of measurement", "enum": ["kg", "piece", "bunch", "box"]},
                "available_p05": {"type": "boolean", "description": "Product availability status (optional, defaults to true)"}
            },
            "required": ["name_p01", "category_p02", "unit_price_p03", "unit_p04"]
        }
    },
    {
        "name": "update_product",
        "description": "BusinessEvent: Update product information - Modify existing product details",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name_p01": {"type": "string", "description": "Name of the product to update (supports fuzzy matching)"},
                "name_p02": {"type": "string", "description": "New product name (optional)"},
                "category_p03": {"type": "string", "description": "New product category (optional)", "enum": ["herbs", "vegetables", "fruits", "other"]},
                "unit_price_p04": {"type": "number", "description": "New price per unit (optional)"},
                "unit_p05": {"type": "string", "description": "New unit of measurement (optional)", "enum": ["kg", "piece", "bunch", "box"]},
                "available_p06": {"type": "boolean", "description": "New availability status (optional)"}
            },
            "required": ["product_name_p01"]
        }
    },
    {
        "name": "delete_client",
        "description": "BusinessEvent: Remove a client from the system - Deactivate or delete a client record",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name_p01": {"type": "string", "description": "Name of the client to delete (supports fuzzy matching)"}
            },
            "required": ["client_name_p01"]
        }
    },
    {
        "name": "delete_product",
        "description": "BusinessEvent: Remove a product from the system - Discontinue or delete a product",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name_p01": {"type": "string", "description": "Name of the product to delete (supports fuzzy matching)"}
            },
            "required": ["product_name_p01"]
        }
    },
    {
        "name": "update_order",
        "description": "BusinessEvent: Update order information - Modify order status or details",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id_p01": {"type": "string", "description": "ID of the order to update"},
                "client_name_p02": {"type": "string", "description": "Name of the client (alternative to order_id, supports fuzzy matching)"},
                "week_p03": {"type": "string", "description": "Week identifier (required if using client_name)"},
                "order_status_p04": {"type": "string", "description": "New order status (optional)", "enum": ["started", "confirmed", "delivered", "paid"]},
                "response_status_p05": {"type": "string", "description": "New response status (optional)", "enum": ["responded", "not_responded", "declined"]}
            },
            "required": []
        }
    },
    {
        "name": "delete_order",
        "description": "BusinessEvent: Cancel or delete an order - Remove an order from the system",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id_p01": {"type": "string", "description": "ID of the order to delete"},
                "client_name_p02": {"type": "string", "description": "Name of the client (alternative to order_id, supports fuzzy matching)"},
                "week_p03": {"type": "string", "description": "Week identifier (required if using client_name)"}
            },
            "required": []
        }
    },
    {
        "name": "update_order_item",
        "description": "BusinessEvent: Update order item quantity or pricing - Modify existing order item details",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id_p01": {"type": "string", "description": "ID of the order containing the item"},
                "product_name_p02": {"type": "string", "description": "Name of the product to update (supports fuzzy matching)"},
                "quantity_p03": {"type": "number", "description": "New quantity (optional)"},
                "unit_price_p04": {"type": "number", "description": "New unit price (optional)"}
            },
            "required": ["order_id_p01", "product_name_p02"]
        }
    },
    {
        "name": "delete_order_item",
        "description": "BusinessEvent: Remove an item from an order - Delete specific product from order",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id_p01": {"type": "string", "description": "ID of the order containing the item"},
                "product_name_p02": {"type": "string", "description": "Name of the product to remove (supports fuzzy matching)"}
            },
            "required": ["order_id_p01", "product_name_p02"]
        }
    },
    
    # Specialized Business Query Functions
    {
        "name": "clients_with_open_payments",
        "description": "Query: Which clients have unpaid orders? - Show all clients who owe money with their outstanding balances",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "clients_not_responded",
        "description": "Query: Which clients haven't responded to order requests? - List clients who haven't placed orders for a specific week",
        "parameters": {
            "type": "object",
            "properties": {
                "week_p01": {"type": "string", "description": "Week identifier to check for responses"}
            },
            "required": ["week_p01"]
        }
    },
    {
        "name": "get_last_week_order",
        "description": "Query: What did a client order last week? - Show the most recent order details for a specific client",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name_p01": {"type": "string", "description": "Name of the client to check (supports fuzzy matching)"}
            },
            "required": ["client_name_p01"]
        }
    },
    {
        "name": "get_current_week",
        "description": "Query: What is the current week identifier? - Get the current week string used by the business",
        "parameters": {"type": "object", "properties": {}, "required": []}
    },
    {
        "name": "calculate_supplier_total",
        "description": "Query: How much product to order from suppliers this week? - Calculate total quantities needed by product for supplier ordering",
        "parameters": {
            "type": "object",
            "properties": {
                "week_p01": {"type": "string", "description": "Week identifier to calculate supplier totals for"}
            },
            "required": ["week_p01"]
        }
    },
    {
        "name": "get_client_order_history",
        "description": "Query: Show all orders for a specific client - Display complete order history with optional limit on number of weeks",
        "parameters": {
            "type": "object",
            "properties": {
                "client_name_p01": {"type": "string", "description": "Name of the client to show history for (supports fuzzy matching)"},
                "weeks_p02": {"type": "integer", "description": "Number of recent weeks to show (optional - shows all if not specified)"}
            },
            "required": ["client_name_p01"]
        }
    }
]
