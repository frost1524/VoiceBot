from tools import (
    check_order_status,
    initiate_return,
    get_refund_status,
    search_products,
    get_account_info,
    escalate_complaint,
    connect_to_agent,
    dispatch_tool,
    TOOL_SCHEMAS,
)


# ── check_order_status ──

def test_check_order_status_known():
    result = check_order_status("ORD001")
    assert result["status"] == "delivered"
    assert result["product"] == "Samsung 43\" Smart TV"


def test_check_order_status_case_insensitive():
    result = check_order_status("ord001")
    assert result["status"] == "delivered"


def test_check_order_status_unknown():
    result = check_order_status("ORD999")
    assert "error" in result


# ── initiate_return ──

def test_initiate_return_delivered_order():
    result = initiate_return("ORD001", "damaged product")
    assert "ticket_id" in result
    assert result["ticket_id"].startswith("RT")
    assert "pickup_date" in result
    assert "refund_eta" in result


def test_initiate_return_non_delivered_order():
    result = initiate_return("ORD002", "wrong item")
    assert "error" in result


def test_initiate_return_unknown_order():
    result = initiate_return("ORD999", "reason")
    assert "error" in result


# ── get_refund_status ──

def test_get_refund_status_processed():
    result = get_refund_status("ORD006")
    assert result["refund_status"] == "processed"
    assert result["refund_amount"] == 1299


def test_get_refund_status_initiated():
    result = get_refund_status("ORD004")
    assert result["refund_status"] == "initiated"
    assert "refund_eta" in result


def test_get_refund_status_not_applicable():
    result = get_refund_status("ORD001")
    assert "error" in result


def test_get_refund_status_unknown():
    result = get_refund_status("ORD999")
    assert "error" in result


# ── search_products ──

def test_search_products_match():
    result = search_products("TV")
    assert result["count"] > 0
    assert any("TV" in p["name"] for p in result["products"])


def test_search_products_category_match():
    result = search_products("Electronics")
    assert result["count"] > 0


def test_search_products_no_match():
    result = search_products("xyzzy_no_match_123")
    assert result["count"] == 0
    assert result["products"] == []


def test_search_products_limited_to_five():
    result = search_products("")
    assert len(result["products"]) <= 5


# ── get_account_info ──

def test_get_account_info_known():
    result = get_account_info("user@example.com")
    assert result["name"] == "Rahul Sharma"
    assert "order_details" in result
    assert len(result["order_details"]) == 3


def test_get_account_info_unknown():
    result = get_account_info("nobody@example.com")
    assert "error" in result


# ── escalate_complaint ──

def test_escalate_complaint_returns_case():
    result = escalate_complaint("ORD001", "item not working")
    assert "case_number" in result
    assert result["case_number"].startswith("CS")
    assert "resolution_sla" in result


# ── connect_to_agent ──

def test_connect_to_agent_returns_queue():
    result = connect_to_agent("cannot resolve", "ORD001")
    assert "queue_position" in result
    assert "wait_time_minutes" in result
    assert "case_number" in result
    assert result["case_number"].startswith("CS")
    assert 1 <= result["queue_position"] <= 5


def test_connect_to_agent_no_order():
    result = connect_to_agent("user requested agent")
    assert "queue_position" in result


# ── dispatch_tool ──

def test_dispatch_tool_routes_correctly():
    result = dispatch_tool("check_order_status", {"order_id": "ORD001"})
    assert result["status"] == "delivered"


def test_dispatch_tool_unknown():
    result = dispatch_tool("nonexistent_tool", {})
    assert "error" in result


def test_dispatch_tool_null_argument_safe():
    result = dispatch_tool("check_order_status", {"order_id": None})
    assert "error" in result


# ── TOOL_SCHEMAS ──

def test_tool_schemas_count():
    assert len(TOOL_SCHEMAS) == 7


def test_tool_schemas_have_required_keys():
    for schema in TOOL_SCHEMAS:
        assert schema["type"] == "function"
        assert "name" in schema
        assert "description" in schema
        assert "parameters" in schema
