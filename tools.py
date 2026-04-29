import json
import random
import string
from datetime import date, timedelta

from mock_data import ORDERS, PRODUCTS, ACCOUNTS


TOOL_SCHEMAS = [
    {
        "type": "function",
        "name": "check_order_status",
        "description": "Check the delivery status and details of a Snapdeal order by order ID.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order ID, e.g. ORD001"},
            },
            "required": ["order_id"],
        },
    },
    {
        "type": "function",
        "name": "initiate_return",
        "description": "Initiate a return request for a delivered Snapdeal order.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order ID to return"},
                "reason": {"type": "string", "description": "Reason for return, e.g. damaged, wrong item, size mismatch"},
            },
            "required": ["order_id", "reason"],
        },
    },
    {
        "type": "function",
        "name": "get_refund_status",
        "description": "Get the refund status for a cancelled or returned Snapdeal order.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order ID to check refund for"},
            },
            "required": ["order_id"],
        },
    },
    {
        "type": "function",
        "name": "search_products",
        "description": "Search for products available on Snapdeal by name or category.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search term, e.g. 'Samsung TV', 'running shoes'"},
            },
            "required": ["query"],
        },
    },
    {
        "type": "function",
        "name": "get_account_info",
        "description": "Get Snapdeal account details and recent orders for a customer by email.",
        "parameters": {
            "type": "object",
            "properties": {
                "email": {"type": "string", "description": "Customer's registered email address"},
            },
            "required": ["email"],
        },
    },
    {
        "type": "function",
        "name": "escalate_complaint",
        "description": "Log a formal complaint for an order issue and get a case number with resolution SLA.",
        "parameters": {
            "type": "object",
            "properties": {
                "order_id": {"type": "string", "description": "Order ID related to the complaint"},
                "issue": {"type": "string", "description": "Description of the issue"},
            },
            "required": ["order_id", "issue"],
        },
    },
    {
        "type": "function",
        "name": "connect_to_agent",
        "description": "Connect the customer to a live human support agent when the issue cannot be resolved by the bot.",
        "parameters": {
            "type": "object",
            "properties": {
                "reason": {"type": "string", "description": "Reason for escalating to a human agent"},
                "order_id": {"type": "string", "description": "Related order ID, if any"},
            },
            "required": ["reason"],
        },
    },
]


def _random_id(prefix: str, length: int = 6) -> str:
    return prefix + "".join(random.choices(string.digits, k=length))


def check_order_status(order_id: str) -> dict:
    order = ORDERS.get(order_id.upper())
    if not order:
        return {"error": f"No order found with ID {order_id}. Please check the order ID and try again."}
    return order


def initiate_return(order_id: str, reason: str) -> dict:
    order = ORDERS.get(order_id.upper())
    if not order:
        return {"error": f"No order found with ID {order_id}."}
    if order["status"] != "delivered":
        return {"error": f"Order {order_id} is not eligible for return. Current status: {order['status']}."}
    pickup_date = (date.today() + timedelta(days=2)).isoformat()
    refund_eta = (date.today() + timedelta(days=7)).isoformat()
    return {
        "ticket_id": _random_id("RT"),
        "order_id": order_id.upper(),
        "product": order["product"],
        "reason": reason,
        "pickup_date": pickup_date,
        "refund_eta": refund_eta,
        "message": f"Return request created. Pickup scheduled for {pickup_date}. Refund expected by {refund_eta}.",
    }


def get_refund_status(order_id: str) -> dict:
    order = ORDERS.get(order_id.upper())
    if not order:
        return {"error": f"No order found with ID {order_id}."}
    if order["status"] == "refund_processed":
        return {
            "order_id": order_id.upper(),
            "refund_status": "processed",
            "refund_amount": order.get("refund_amount", order["amount"]),
            "refund_date": order.get("refund_date"),
            "refund_method": order.get("refund_method", "Original payment method"),
        }
    if order["status"] == "cancelled":
        return {
            "order_id": order_id.upper(),
            "refund_status": "initiated",
            "refund_amount": order["amount"],
            "refund_eta": order.get("refund_eta"),
            "message": "Refund initiated. Will be credited within 5-7 business days.",
        }
    if order["status"] == "return_initiated":
        return {
            "order_id": order_id.upper(),
            "refund_status": "pending_pickup",
            "message": "Refund will be processed after the item is picked up.",
        }
    return {"error": f"No refund applicable for order {order_id} with status '{order['status']}'."}


def search_products(query: str) -> dict:
    q = query.lower()
    matches = [p for p in PRODUCTS if q in p["name"].lower() or q in p["category"].lower()]
    return {"query": query, "count": len(matches), "products": matches[:5]}


def get_account_info(email: str) -> dict:
    account = ACCOUNTS.get(email.lower())
    if not account:
        return {"error": f"No account found with email {email}."}
    order_details = [ORDERS[oid] for oid in account["recent_orders"] if oid in ORDERS]
    return {**account, "order_details": order_details}


def escalate_complaint(order_id: str, issue: str) -> dict:
    return {
        "case_number": _random_id("CS"),
        "order_id": order_id,
        "issue": issue,
        "resolution_sla": "24-48 hours",
        "message": "Complaint logged. Our team will contact you within 24-48 hours.",
    }


def connect_to_agent(reason: str, order_id: str = None) -> dict:
    queue_position = random.randint(1, 5)
    wait_time = queue_position * 2
    return {
        "case_number": _random_id("CS"),
        "queue_position": queue_position,
        "wait_time_minutes": wait_time,
        "reason": reason,
        "order_id": order_id,
        "message": f"You are #{queue_position} in queue. Estimated wait: {wait_time} minutes.",
    }


def dispatch_tool(name: str, arguments: dict) -> dict:
    handlers = {
        "check_order_status": lambda: check_order_status(arguments.get("order_id", "")),
        "initiate_return": lambda: initiate_return(arguments.get("order_id", ""), arguments.get("reason", "")),
        "get_refund_status": lambda: get_refund_status(arguments.get("order_id", "")),
        "search_products": lambda: search_products(arguments.get("query", "")),
        "get_account_info": lambda: get_account_info(arguments.get("email", "")),
        "escalate_complaint": lambda: escalate_complaint(arguments.get("order_id", ""), arguments.get("issue", "")),
        "connect_to_agent": lambda: connect_to_agent(arguments.get("reason", ""), arguments.get("order_id")),
    }
    handler = handlers.get(name)
    if handler:
        return handler()
    return {"error": f"Unknown tool: {name}"}
