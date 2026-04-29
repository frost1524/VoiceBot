from mock_data import ORDERS, PRODUCTS, ACCOUNTS

VALID_STATUSES = {
    "delivered", "in_transit", "delayed",
    "cancelled", "return_initiated", "refund_processed",
}


def test_orders_count():
    assert len(ORDERS) == 6


def test_orders_have_required_fields():
    for order_id, order in ORDERS.items():
        assert order["id"] == order_id, f"{order_id} id mismatch"
        assert "product" in order
        assert "status" in order
        assert "amount" in order


def test_order_statuses_are_valid():
    for order_id, order in ORDERS.items():
        assert order["status"] in VALID_STATUSES, f"{order_id} has invalid status {order['status']}"


def test_one_order_per_status():
    statuses = [o["status"] for o in ORDERS.values()]
    for s in VALID_STATUSES:
        assert s in statuses, f"No order with status {s}"


def test_products_count():
    assert len(PRODUCTS) == 15


def test_products_have_required_fields():
    for p in PRODUCTS:
        assert "id" in p
        assert "name" in p
        assert "price" in p
        assert isinstance(p["price"], (int, float))
        assert "in_stock" in p
        assert isinstance(p["in_stock"], bool)
        assert "category" in p
        assert "rating" in p


def test_products_cover_three_categories():
    categories = {p["category"] for p in PRODUCTS}
    assert "Electronics" in categories
    assert "Clothing" in categories
    assert "Home & Kitchen" in categories


def test_accounts_count():
    assert len(ACCOUNTS) == 2


def test_accounts_have_required_fields():
    for email, account in ACCOUNTS.items():
        assert account["email"] == email
        assert "name" in account
        assert "status" in account
        assert "recent_orders" in account
        assert isinstance(account["recent_orders"], list)


def test_account_orders_exist_in_orders():
    for email, account in ACCOUNTS.items():
        for oid in account["recent_orders"]:
            assert oid in ORDERS, f"{email} references unknown order {oid}"
