% Epicure Gourmet Business Simulation Schema
% Generated from MetaModel v3.0 - Updated to Latest Standards
% Includes complete CRUD coverage for all Business Objects

% Turn off singleton variable warnings
:- style_check(-singleton).

:- dynamic client/5.
:- dynamic order/5.
:- dynamic product/6.
:- dynamic order_item/5.
:- dynamic alias/3.

% Load data facts
:- consult('data.pl').

% ============================================================================
% ALIAS SUPPORT FUNCTIONS
% ============================================================================

% List all aliases for preprocessing
list_all_aliases(Aliases) :-
    findall([Alias, Type, FullName], alias(Alias, Type, FullName), Aliases).

% Find fuzzy matches for a term
find_fuzzy_matches(Term, Type, Matches) :-
    findall([Name, Distance], 
        (alias(Alias, Type, Name), 
         levenshtein_distance(Term, Alias, Distance),
         Distance =< 2), 
        UnsortedMatches),
    sort(2, @=<, UnsortedMatches, Matches).

% Simple Levenshtein distance implementation
levenshtein_distance(S1, S2, Distance) :-
    atom_chars(S1, L1),
    atom_chars(S2, L2),
    levenshtein_list(L1, L2, Distance).

levenshtein_list([], L2, N) :- length(L2, N).
levenshtein_list(L1, [], N) :- length(L1, N).
levenshtein_list([H|T1], [H|T2], N) :- 
    levenshtein_list(T1, T2, N).
levenshtein_list([H1|T1], [H2|T2], N) :-
    H1 \= H2,
    levenshtein_list(T1, [H2|T2], N1),
    levenshtein_list([H1|T1], T2, N2),
    levenshtein_list(T1, T2, N3),
    N is 1 + min(N1, min(N2, N3)).

% ============================================================================
% CLIENT CRUD FUNCTIONS
% ============================================================================

% Wrapper functions for LLM interface - handle optional parameters
% 0 parameters (no filter)
list_all_clients(Result) :- 
    list_all_clients('', Result).

% List all clients - FIXES "show my clients" error
list_all_clients(ClientType, Result) :-
    (ClientType = '' ->
        findall([ID, Name, ContactType, ContactInfo, Type], 
            client(ID, Name, ContactType, ContactInfo, Type), 
            Clients)
    ;
        findall([ID, Name, ContactType, ContactInfo, ClientType], 
            client(ID, Name, ContactType, ContactInfo, ClientType), 
            Clients)
    ),
    length(Clients, Count),
    (Count = 0 ->
        Result = 'No clients found in the system.'
    ;
        format_client_list(Clients, FormattedList),
        atom_number(CountAtom, Count),
        atomic_list_concat(['Found ', CountAtom, ' clients:', '\n', FormattedList], Result)
    ).

% Format client list for display
format_client_list([], '').
format_client_list([[ID, Name, ContactType, ContactInfo, Type]|Rest], Result) :-
    format_client_list(Rest, RestFormatted),
    atomic_list_concat(['- ', Name, ' (', Type, ') - ', ContactType, ': ', ContactInfo, '\n', RestFormatted], Result).

% Create new client
create_client(Name, ContactType, ContactInfo, ClientType, Result) :-
    % Generate new ID
    findall(ID, client(ID, _, _, _, _), IDs),
    (IDs = [] -> 
        NewID = 'client_001'
    ;
        length(IDs, Count),
        NextNum is Count + 1,
        format(atom(NewID), 'client_~|~`0t~d~3+', [NextNum])
    ),
    % Check if client already exists
    (client(_, Name, _, _, _) ->
        Result = 'Error: Client with this name already exists.'
    ;
        % Create the client
        assertz(client(NewID, Name, ContactType, ContactInfo, ClientType)),
        atomic_list_concat(['Client "', Name, '" created successfully with ID: ', NewID], Result)
    ).

% Update client information
update_client(ClientName, NewName, NewContactType, NewContactInfo, NewClientType, Result) :-
    find_client_fuzzy(ClientName, Matches),
    (Matches = [] ->
        Result = 'Error: No client found matching that name.'
    ;
        Matches = [ClientID-_] ->
        % Single match - proceed with update
        retract(client(ClientID, OldName, OldContactType, OldContactInfo, OldClientType)),
        (NewName = '' -> UpdatedName = OldName ; UpdatedName = NewName),
        (NewContactType = '' -> UpdatedContactType = OldContactType ; UpdatedContactType = NewContactType),
        (NewContactInfo = '' -> UpdatedContactInfo = OldContactInfo ; UpdatedContactInfo = NewContactInfo),
        (NewClientType = '' -> UpdatedClientType = OldClientType ; UpdatedClientType = NewClientType),
        assertz(client(ClientID, UpdatedName, UpdatedContactType, UpdatedContactInfo, UpdatedClientType)),
        atomic_list_concat(['Client "', OldName, '" updated successfully.'], Result)
    ;
        % Multiple matches
        format_multiple_matches(Matches, 'client', FormattedMatches),
        atomic_list_concat(['Multiple clients found:\n', FormattedMatches], Result)
    ).

% ============================================================================
% PRODUCT CRUD FUNCTIONS
% ============================================================================

% Wrapper functions for LLM interface - handle optional parameters
% 0 parameters (no filter)
list_all_products(Result) :- 
    list_all_products('', Result).

% List all products
list_all_products(Category, Result) :-
    (Category = '' ->
        findall([ID, Name, Cat, UnitPrice, Unit, Available], 
            product(ID, Name, Cat, UnitPrice, Unit, Available), 
            Products)
    ;
        findall([ID, Name, Cat, UnitPrice, Unit, Available], 
            product(ID, Name, Category, UnitPrice, Unit, Available), 
            Products)
    ),
    length(Products, Count),
    (Count = 0 ->
        Result = 'No products found in the system.'
    ;
        format_product_list(Products, FormattedList),
        atom_number(CountAtom, Count),
        atomic_list_concat(['Found ', CountAtom, ' products:', '\n', FormattedList], Result)
    ).

% Format product list for display
format_product_list([], '').
format_product_list([[ID, Name, Category, UnitPrice, Unit, Available]|Rest], Result) :-
    format_product_list(Rest, RestFormatted),
    (Available = true -> Status = 'Available' ; Status = 'Unavailable'),
    atomic_list_concat(['- ', Name, ' (', Category, ') - $', UnitPrice, '/', Unit, ' - ', Status, '\n', RestFormatted], Result).

% Create new product
create_product(Name, Category, UnitPrice, Unit, Available, Result) :-
    % Generate new ID
    findall(ID, product(ID, _, _, _, _, _), IDs),
    (IDs = [] -> 
        NewID = 'product_001'
    ;
        length(IDs, Count),
        NextNum is Count + 1,
        format(atom(NewID), 'product_~|~`0t~d~3+', [NextNum])
    ),
    % Check if product already exists
    (product(_, Name, _, _, _, _) ->
        Result = 'Error: Product with this name already exists.'
    ;
        % Create the product
        assertz(product(NewID, Name, Category, UnitPrice, Unit, Available)),
        atomic_list_concat(['Product "', Name, '" created successfully with ID: ', NewID], Result)
    ).

% Update product information
update_product(ProductName, NewName, NewCategory, NewUnitPrice, NewUnit, NewAvailable, Result) :-
    find_product_fuzzy(ProductName, Matches),
    (Matches = [] ->
        Result = 'Error: No product found matching that name.'
    ;
        Matches = [ProductID-_] ->
        % Single match - proceed with update
        retract(product(ProductID, OldName, OldCategory, OldUnitPrice, OldUnit, OldAvailable)),
        (NewName = '' -> UpdatedName = OldName ; UpdatedName = NewName),
        (NewCategory = '' -> UpdatedCategory = OldCategory ; UpdatedCategory = NewCategory),
        (NewUnitPrice = '' -> UpdatedUnitPrice = OldUnitPrice ; UpdatedUnitPrice = NewUnitPrice),
        (NewUnit = '' -> UpdatedUnit = OldUnit ; UpdatedUnit = NewUnit),
        (NewAvailable = '' -> UpdatedAvailable = OldAvailable ; UpdatedAvailable = NewAvailable),
        assertz(product(ProductID, UpdatedName, UpdatedCategory, UpdatedUnitPrice, UpdatedUnit, UpdatedAvailable)),
        atomic_list_concat(['Product "', OldName, '" updated successfully.'], Result)
    ;
        % Multiple matches
        format_multiple_matches(Matches, 'product', FormattedMatches),
        atomic_list_concat(['Multiple products found:\n', FormattedMatches], Result)
    ).

% ============================================================================
% ORDER CRUD FUNCTIONS
% ============================================================================

% Wrapper functions for LLM interface - handle optional parameters
% 0 parameters (no filters)
list_all_orders(Result) :- 
    list_all_orders('', '', Result).

% 1 parameter (week only)
list_all_orders(Week, Result) :- 
    list_all_orders(Week, '', Result).

% List all orders
list_all_orders(Week, Status, Result) :-
    (Week = '', Status = '' ->
        findall([ID, ClientID, W, OrderStatus, ResponseStatus], 
            order(ID, ClientID, W, OrderStatus, ResponseStatus), 
            Orders)
    ; Week \= '', Status = '' ->
        findall([ID, ClientID, W, OrderStatus, ResponseStatus], 
            order(ID, ClientID, Week, OrderStatus, ResponseStatus), 
            Orders)
    ; Week = '', Status \= '' ->
        findall([ID, ClientID, W, OrderStatus, ResponseStatus], 
            order(ID, ClientID, W, Status, ResponseStatus), 
            Orders)
    ;
        findall([ID, ClientID, W, OrderStatus, ResponseStatus], 
            order(ID, ClientID, Week, Status, ResponseStatus), 
            Orders)
    ),
    length(Orders, Count),
    (Count = 0 ->
        Result = 'No orders found matching the criteria.'
    ;
        format_order_list(Orders, FormattedList),
        atom_number(CountAtom, Count),
        atomic_list_concat(['Found ', CountAtom, ' orders:', '\n', FormattedList], Result)
    ).

% Format order list for display
format_order_list([], '').
format_order_list([[ID, ClientID, Week, OrderStatus, ResponseStatus]|Rest], Result) :-
    format_order_list(Rest, RestFormatted),
    client(ClientID, ClientName, _, _, _),
    calculate_order_total(ID, Total),
    atomic_list_concat(['- Order ', ID, ' - ', ClientName, ' (', Week, ') - ', OrderStatus, ' - $', Total, '\n', RestFormatted], Result).

% ============================================================================
% EXISTING BUSINESS FUNCTIONS (Enhanced)
% ============================================================================

% Record payment with enhanced error handling
record_payment(ClientName, Amount, PaymentMethod, Result) :-
    find_client_fuzzy(ClientName, Matches),
    (Matches = [] ->
        Result = 'Error: No client found matching that name.'
    ;
        Matches = [ClientID-_] ->
        % Single match - find orders by amount
        findall(OrderID, 
            (order(OrderID, ClientID, _, OrderStatus, _),
             OrderStatus \= paid,
             calculate_order_total(OrderID, Amount)), 
            MatchingOrders),
        (MatchingOrders = [] ->
            atomic_list_concat(['No unpaid orders found for amount $', Amount, ' for client "', ClientName, '".'], Result)
        ;
            MatchingOrders = [OrderID] ->
            % Single order match - mark as paid
            retract(order(OrderID, ClientID, Week, _, ResponseStatus)),
            assertz(order(OrderID, ClientID, Week, paid, ResponseStatus)),
            atomic_list_concat(['Payment of $', Amount, ' recorded for "', ClientName, '" via ', PaymentMethod, '. Order ', OrderID, ' marked as paid.'], Result)
        ;
            % Multiple order matches
            atomic_list_concat(MatchingOrders, ', ', OrderList),
            atomic_list_concat(['Multiple orders found with amount $', Amount, ': ', OrderList, '. Please specify which order.'], Result)
        )
    ;
        % Multiple client matches
        format_multiple_matches(Matches, 'client', FormattedMatches),
        atomic_list_concat(['Multiple clients found:\n', FormattedMatches], Result)
    ).

% Create order with validation
create_order(ClientName, Week, Result) :-
    find_client_fuzzy(ClientName, Matches),
    (Matches = [] ->
        Result = 'Error: No client found matching that name.'
    ;
        Matches = [ClientID-_] ->
        % Check if order already exists for this week
        (order(_, ClientID, Week, _, _) ->
            Result = 'Error: Order already exists for this client and week.'
        ;
            % Generate new order ID
            findall(ID, order(ID, _, _, _, _), IDs),
            length(IDs, Count),
            NextNum is Count + 1,
            format(atom(NewOrderID), 'order_~|~`0t~d~3+', [NextNum]),
            % Create the order
            assertz(order(NewOrderID, ClientID, Week, started, not_responded)),
            client(ClientID, ClientName, _, _, _),
            atomic_list_concat(['Order ', NewOrderID, ' created for "', ClientName, '" for week ', Week, '.'], Result)
        )
    ;
        % Multiple matches
        format_multiple_matches(Matches, 'client', FormattedMatches),
        atomic_list_concat(['Multiple clients found:\n', FormattedMatches], Result)
    ).

% Add order item with validation
add_order_item(OrderID, ProductName, Quantity, UnitPrice, Result) :-
    (order(OrderID, _, _, _, _) ->
        find_product_fuzzy(ProductName, Matches),
        (Matches = [] ->
            Result = 'Error: No product found matching that name.'
        ;
            Matches = [ProductID-_] ->
            % Get product price if not specified
            product(ProductID, ProductName, _, DefaultPrice, Unit, Available),
            (Available = false ->
                Result = 'Error: Product is not available.'
            ;
                (UnitPrice = '' -> FinalPrice = DefaultPrice ; FinalPrice = UnitPrice),
                % Generate new order item ID
                findall(ID, order_item(ID, _, _, _, _), IDs),
                length(IDs, Count),
                NextNum is Count + 1,
                format(atom(NewItemID), 'item_~|~`0t~d~3+', [NextNum]),
                % Create the order item
                assertz(order_item(NewItemID, OrderID, ProductID, Quantity, FinalPrice)),
                LineTotal is Quantity * FinalPrice,
                atomic_list_concat(['Added ', Quantity, ' ', Unit, ' of "', ProductName, '" to order ', OrderID, ' at $', FinalPrice, '/', Unit, ' (Total: $', LineTotal, ').'], Result)
            )
        ;
            % Multiple matches
            format_multiple_matches(Matches, 'product', FormattedMatches),
            atomic_list_concat(['Multiple products found:\n', FormattedMatches], Result)
        )
    ;
        Result = 'Error: Order not found.'
    ).

% Start new week with validation
start_new_week(WeekDate, Result) :-
    % Check if week already exists
    (order(_, _, WeekDate, _, _) ->
        Result = 'Error: Orders already exist for this week.'
    ;
        % Create orders for all active clients
        findall(ClientID, client(ClientID, _, _, _, _), ClientIDs),
        create_weekly_orders(ClientIDs, WeekDate, 1, OrderCount),
        atomic_list_concat(['Started new week for ', WeekDate, '. Created ', OrderCount, ' initial orders.'], Result)
    ).

% Helper to create weekly orders
create_weekly_orders([], _, Count, Count).
create_weekly_orders([ClientID|Rest], Week, CurrentCount, FinalCount) :-
    findall(ID, order(ID, _, _, _, _), IDs),
    length(IDs, ExistingCount),
    NextNum is ExistingCount + CurrentCount,
    format(atom(NewOrderID), 'order_~|~`0t~d~3+', [NextNum]),
    assertz(order(NewOrderID, ClientID, Week, started, not_responded)),
    NextCount is CurrentCount + 1,
    create_weekly_orders(Rest, Week, NextCount, FinalCount).

% Mark client responded
mark_client_responded(ClientName, Week, Response, Result) :-
    find_client_fuzzy(ClientName, Matches),
    (Matches = [] ->
        Result = 'Error: No client found matching that name.'
    ;
        Matches = [ClientID-_] ->
        (order(OrderID, ClientID, Week, OrderStatus, _) ->
            retract(order(OrderID, ClientID, Week, OrderStatus, _)),
            assertz(order(OrderID, ClientID, Week, OrderStatus, Response)),
            client(ClientID, ClientName, _, _, _),
            atomic_list_concat(['Marked "', ClientName, '" as "', Response, '" for week ', Week, '.'], Result)
        ;
            Result = 'Error: No order found for this client and week.'
        )
    ;
        % Multiple matches
        format_multiple_matches(Matches, 'client', FormattedMatches),
        atomic_list_concat(['Multiple clients found:\n', FormattedMatches], Result)
    ).

% ============================================================================
% QUERY FUNCTIONS (Enhanced)
% ============================================================================

% Clients with open payments
clients_with_open_payments(Result) :-
    findall([ClientID, ClientName, Balance, OrderCount], 
        (client(ClientID, ClientName, _, _, _),
         calculate_client_balance(ClientID, Balance),
         Balance > 0,
         count_unpaid_orders(ClientID, OrderCount)), 
        ClientsWithBalance),
    (ClientsWithBalance = [] ->
        Result = 'No clients have outstanding payments.'
    ;
        format_balance_list(ClientsWithBalance, FormattedList),
        atomic_list_concat(['Clients with outstanding payments:\n', FormattedList], Result)
    ).

% Clients not responded
clients_not_responded(Week, Result) :-
    findall([ClientID, ClientName, ContactInfo], 
        (client(ClientID, ClientName, _, ContactInfo, _),
         order(_, ClientID, Week, _, not_responded)), 
        ClientsNotResponded),
    (ClientsNotResponded = [] ->
        atomic_list_concat(['All clients have responded for week ', Week, '.'], Result)
    ;
        format_contact_list(ClientsNotResponded, FormattedList),
        atomic_list_concat(['Clients who have not responded for week ', Week, ':\n', FormattedList], Result)
    ).

% Get last week order
get_last_week_order(ClientName, Result) :-
    find_client_fuzzy(ClientName, Matches),
    (Matches = [] ->
        Result = 'Error: No client found matching that name.'
    ;
        Matches = [ClientID-_] ->
        % Find most recent order
        findall([Week, OrderID], order(OrderID, ClientID, Week, _, _), Orders),
        (Orders = [] ->
            Result = 'No orders found for this client.'
        ;
            sort(1, @>=, Orders, SortedOrders),
            SortedOrders = [[LastWeek, LastOrderID]|_],
            format_order_details(LastOrderID, OrderDetails),
            atomic_list_concat(['Last order for "', ClientName, '" (Week ', LastWeek, '):\n', OrderDetails], Result)
        )
    ;
        % Multiple matches
        format_multiple_matches(Matches, 'client', FormattedMatches),
        atomic_list_concat(['Multiple clients found:\n', FormattedMatches], Result)
    ).

% Get current week
get_current_week(Result) :-
    get_time(TimeStamp),
    format_time(atom(CurrentWeek), '%Y-W%V', TimeStamp),
    atomic_list_concat(['Current week: ', CurrentWeek], Result).

% Calculate supplier total
calculate_supplier_total(Week, Result) :-
    findall([ProductID, ProductName, TotalQuantity], 
        (product(ProductID, ProductName, _, _, Unit, _),
         aggregate_sum(Quantity, 
            (order(OrderID, _, Week, _, _),
             order_item(_, OrderID, ProductID, Quantity, _)), 
            TotalQuantity),
         TotalQuantity > 0), 
        ProductTotals),
    (ProductTotals = [] ->
        atomic_list_concat(['No products ordered for week ', Week, '.'], Result)
    ;
        format_supplier_totals(ProductTotals, FormattedTotals),
        atomic_list_concat(['Supplier totals for week ', Week, ':\n', FormattedTotals], Result)
    ).

% Get client order history
get_client_order_history(ClientName, Weeks, Result) :-
    find_client_fuzzy(ClientName, Matches),
    (Matches = [] ->
        Result = 'Error: No client found matching that name.'
    ;
        Matches = [ClientID-_] ->
        findall([Week, OrderID, Total], 
            (order(OrderID, ClientID, Week, _, _),
             calculate_order_total(OrderID, Total)), 
            OrderHistory),
        (OrderHistory = [] ->
            Result = 'No order history found for this client.'
        ;
            sort(1, @>=, OrderHistory, SortedHistory),
            (Weeks = '' -> 
                LimitedHistory = SortedHistory
            ;
                length(LimitedHistory, Weeks),
                append(LimitedHistory, _, SortedHistory)
            ),
            format_order_history(LimitedHistory, FormattedHistory),
            client(ClientID, ClientName, _, _, _),
            atomic_list_concat(['Order history for "', ClientName, '":\n', FormattedHistory], Result)
        )
    ;
        % Multiple matches
        format_multiple_matches(Matches, 'client', FormattedMatches),
        atomic_list_concat(['Multiple clients found:\n', FormattedMatches], Result)
    ).

% ============================================================================
% HELPER FUNCTIONS
% ============================================================================

% Find client with fuzzy matching
find_client_fuzzy(ClientName, Matches) :-
    findall(ClientID-FullName, 
        (client(ClientID, FullName, _, _, _),
         (sub_atom(FullName, _, _, _, ClientName) ; 
          alias(ClientName, client, FullName))), 
        ExactMatches),
    (ExactMatches \= [] ->
        Matches = ExactMatches
    ;
        find_fuzzy_matches(ClientName, client, FuzzyMatches),
        findall(ClientID-FullName,
            (member([FullName, _], FuzzyMatches),
             client(ClientID, FullName, _, _, _)),
            Matches)
    ).

% Find product with fuzzy matching
find_product_fuzzy(ProductName, Matches) :-
    findall(ProductID-FullName, 
        (product(ProductID, FullName, _, _, _, _),
         (sub_atom(FullName, _, _, _, ProductName) ; 
          alias(ProductName, product, FullName))), 
        ExactMatches),
    (ExactMatches \= [] ->
        Matches = ExactMatches
    ;
        find_fuzzy_matches(ProductName, product, FuzzyMatches),
        findall(ProductID-FullName,
            (member([FullName, _], FuzzyMatches),
             product(ProductID, FullName, _, _, _, _)),
            Matches)
    ).

% Calculate order total
calculate_order_total(OrderID, Total) :-
    findall(LineTotal, 
        (order_item(_, OrderID, _, Quantity, UnitPrice),
         LineTotal is Quantity * UnitPrice), 
        LineTotals),
    sum_list(LineTotals, Total).

% Calculate client balance
calculate_client_balance(ClientID, Balance) :-
    findall(Total, 
        (order(OrderID, ClientID, _, OrderStatus, _),
         OrderStatus \= paid,
         calculate_order_total(OrderID, Total)), 
        UnpaidTotals),
    sum_list(UnpaidTotals, Balance).

% Count unpaid orders
count_unpaid_orders(ClientID, Count) :-
    findall(OrderID, 
        (order(OrderID, ClientID, _, OrderStatus, _),
         OrderStatus \= paid), 
        UnpaidOrders),
    length(UnpaidOrders, Count).

% Format multiple matches
format_multiple_matches([], _, '').
format_multiple_matches([_-Name|Rest], Type, Result) :-
    format_multiple_matches(Rest, Type, RestFormatted),
    atomic_list_concat(['- ', Name, ' (', Type, ')\n', RestFormatted], Result).

% Format balance list
format_balance_list([], '').
format_balance_list([[_, ClientName, Balance, OrderCount]|Rest], Result) :-
    format_balance_list(Rest, RestFormatted),
    atomic_list_concat(['- ', ClientName, ': $', Balance, ' (', OrderCount, ' unpaid orders)\n', RestFormatted], Result).

% Format contact list
format_contact_list([], '').
format_contact_list([[_, ClientName, ContactInfo]|Rest], Result) :-
    format_contact_list(Rest, RestFormatted),
    atomic_list_concat(['- ', ClientName, ' - ', ContactInfo, '\n', RestFormatted], Result).

% Format order details
format_order_details(OrderID, Details) :-
    findall([ProductName, Quantity, UnitPrice, Unit], 
        (order_item(_, OrderID, ProductID, Quantity, UnitPrice),
         product(ProductID, ProductName, _, _, Unit, _)), 
        Items),
    format_order_items(Items, ItemsFormatted),
    calculate_order_total(OrderID, Total),
    atomic_list_concat([ItemsFormatted, 'Total: $', Total], Details).

% Format order items
format_order_items([], '').
format_order_items([[ProductName, Quantity, UnitPrice, Unit]|Rest], Result) :-
    format_order_items(Rest, RestFormatted),
    LineTotal is Quantity * UnitPrice,
    atomic_list_concat(['- ', Quantity, ' ', Unit, ' ', ProductName, ' @ $', UnitPrice, '/', Unit, ' = $', LineTotal, '\n', RestFormatted], Result).

% Format supplier totals
format_supplier_totals([], '').
format_supplier_totals([[_, ProductName, TotalQuantity]|Rest], Result) :-
    format_supplier_totals(Rest, RestFormatted),
    atomic_list_concat(['- ', ProductName, ': ', TotalQuantity, '\n', RestFormatted], Result).

% Format order history
format_order_history([], '').
format_order_history([[Week, OrderID, Total]|Rest], Result) :-
    format_order_history(Rest, RestFormatted),
    atomic_list_concat(['- Week ', Week, ' (Order ', OrderID, '): $', Total, '\n', RestFormatted], Result).

% Aggregate sum helper
aggregate_sum(Template, Goal, Sum) :-
    findall(Template, Goal, Values),
    sum_list(Values, Sum).

% ============================================================================
% UNIVERSAL QUERY FUNCTIONS WITH PROLOG VARIABLE BINDING
% ============================================================================

% Universal client query function - with integrated formatting
get_clients(P01, P02, P03, P04, P05) :- 
    client(P01, P02, P03, P04, P05),
    format_named_output(client, [id_p01,name_p02,contact_type_p03,contact_info_p04,client_type_p05], [P01,P02,P03,P04,P05]).

% Universal product query function - with integrated formatting
get_products(P01, P02, P03, P04, P05, P06) :- 
    product(P01, P02, P03, P04, P05, P06),
    format_named_output(product, [id_p01,name_p02,category_p03,unit_price_p04,unit_p05,available_p06], [P01,P02,P03,P04,P05,P06]).

% Universal order query function - with integrated formatting
get_orders(P01, P02, P03, P04, P05) :- 
    order(P01, P02, P03, P04, P05),
    format_named_output(order, [id_p01,client_id_p02,week_p03,order_status_p04,response_status_p05], [P01,P02,P03,P04,P05]).

% ============================================================================
% GENERIC OUTPUT FORMATTING PREDICATES
% ============================================================================

% Format named output for LLM consumption
% format_named_output(EntityName, FieldNames, Values)
% Example: format_named_output(product, [id_p01,name_p02], ['prod_001','Albahaca'])
% Output: product(id_p01='prod_001', name_p02='Albahaca')
format_named_output(EntityName, FieldNames, Values) :-
    zip_params(FieldNames, Values, NamedParams),
    atomic_list_concat(NamedParams, ', ', ParamsStr),
    format('~w(~w)~n', [EntityName, ParamsStr]).

% Zip field names with values to create name=value pairs
% zip_params([name1,name2], [val1,val2], ['name1=val1','name2=val2'])
zip_params([], [], []).
zip_params([Name|Names], [Value|Values], [NamedParam|Rest]) :-
    format_param_value(Name, Value, NamedParam),
    zip_params(Names, Values, Rest).

% Format individual parameter with proper quoting
% format_param_value(name, value, 'name=value')
format_param_value(Name, Value, NamedParam) :-
    (   atom(Value) ->
        format(atom(NamedParam), '~w=~q', [Name, Value])
    ;   number(Value) ->
        format(atom(NamedParam), '~w=~w', [Name, Value])
    ;   Value == true ->
        format(atom(NamedParam), '~w=true', [Name])
    ;   Value == false ->
        format(atom(NamedParam), '~w=false', [Name])
    ;   % Default case - quote everything else
        format(atom(NamedParam), '~w=~q', [Name, Value])
    ).
