import logging
from fastapi import APIRouter, HTTPException, Header, Request, Body, Query
from typing import Dict, Any, List, Optional
from pydantic import BaseModel
import json
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/testing",
    tags=["testing"],
    responses={404: {"description": "Not found"}},
)

# Pydantic models for testing
class UserData(BaseModel):
    user_id: str
    name: str
    email: str
    age: Optional[int] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": "usr_12345",
                "name": "Nguyen Van A",
                "email": "nguyenvana@example.com",
                "age": 25
            }
        }

class ProductInfo(BaseModel):
    product_id: str
    name: str
    price: float
    category: str
    in_stock: bool
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    weight: Optional[float] = None
    dimensions: Optional[Dict[str, float]] = None
    supplier_info: Optional[Dict[str, Any]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "prod_001",
                "name": "iPhone 15 Pro Max",
                "price": 29990000.0,
                "category": "Electronics",
                "in_stock": True,
                "description": "Latest iPhone with advanced camera system",
                "tags": ["smartphone", "apple", "5G", "camera"],
                "weight": 221.0,
                "dimensions": {"length": 159.9, "width": 76.7, "height": 8.25},
                "supplier_info": {
                    "supplier_id": "SUP_001",
                    "name": "Apple Inc.",
                    "contact": "+1-800-275-2273"
                }
            }
        }

class OrderRequest(BaseModel):
    order_id: str
    items: List[Dict[str, Any]]
    customer_info: Dict[str, str]
    total_amount: float
    
    class Config:
        json_schema_extra = {
            "example": {
                "order_id": "ORD_20240115_001",
                "items": [
                    {
                        "product_id": "prod_001",
                        "name": "iPhone 15 Pro Max",
                        "quantity": 1,
                        "unit_price": 29990000.0,
                        "total_price": 29990000.0
                    },
                    {
                        "product_id": "prod_002", 
                        "name": "AirPods Pro",
                        "quantity": 2,
                        "unit_price": 6490000.0,
                        "total_price": 12980000.0
                    }
                ],
                "customer_info": {
                    "customer_id": "cust_123",
                    "name": "Tran Thi B",
                    "email": "tranthib@example.com",
                    "phone": "0987654321",
                    "address": "123 Nguyen Hue, Q1, TP.HCM"
                },
                "total_amount": 42970000.0
            }
        }

class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: str


@router.get("/api_1")
async def api_1(
    request: Request,
    x_api_key: str = Header(None, alias="X-API-Key", example="api_key_12345_abcdef"),
    x_request_id: str = Header(None, alias="X-Request-ID", example="req_20240115_001"),
    user_agent: str = Header(None, alias="User-Agent", example="Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0")
):
    """
    Testing API 1 - GET method with custom headers
    Simulates a user profile retrieval endpoint
    """
    try:
        # Fake response with headers validation
        response_data = {
            "user_profile": {
                "user_id": "user_12345",
                "username": "test_user",
                "email": "test@example.com",
                "status": "active",
                "last_login": "2024-01-15T10:30:00Z",
                "permissions": ["read", "write", "admin"]
            },
            "request_headers": {
                "api_key": x_api_key or "missing",
                "request_id": x_request_id or "auto-generated",
                "user_agent": user_agent or "unknown"
            }
        }
        
        return ApiResponse(
            success=True,
            message="User profile retrieved successfully",
            data=response_data,
            timestamp=datetime.now().isoformat()
        )
    except Exception as e:
        logger.error(f"Error in api_1: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/api_2")
async def api_2(
    user_data: UserData,
    authorization: str = Header(None, alias="Authorization", example="Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"),
    content_type: str = Header("application/json", alias="Content-Type", example="application/json"),
    x_client_version: str = Header("1.0.0", alias="X-Client-Version", example="2.1.5")
):
    """
    Testing API 2 - POST method with JSON body and authentication headers
    Simulates a user registration endpoint
    """
    try:
        # Simulate validation
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Invalid or missing authorization token")
        
        # Fake user creation response
        response_data = {
            "created_user": {
                "user_id": f"usr_{user_data.name.lower()}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "name": user_data.name,
                "email": user_data.email,
                "age": user_data.age,
                "status": "active",
                "created_at": datetime.now().isoformat(),
                "account_type": "premium" if user_data.age and user_data.age >= 18 else "standard"
            },
            "request_metadata": {
                "authorization_type": authorization.split(" ")[0] if " " in authorization else "unknown",
                "content_type": content_type,
                "client_version": x_client_version
            }
        }
        
        return ApiResponse(
            success=True,
            message="User created successfully",
            data=response_data,
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in api_2: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/api_3")
async def api_3(
    product_info: ProductInfo,
    request: Request,
    # Required headers
    x_store_id: str = Header(..., alias="X-Store-ID", example="STORE_HCM_001"),
    x_merchant_key: str = Header(..., alias="X-Merchant-Key", example="merchant_key_xyz789_secure"),
    
    # Optional headers with defaults
    accept: str = Header("application/json", alias="Accept", example="application/json"),
    x_client_version: str = Header("1.0.0", alias="X-Client-Version", example="2.1.5"),
    x_request_id: str = Header(None, alias="X-Request-ID", example="req_20240115_001"),
    x_user_agent: str = Header(None, alias="X-User-Agent", example="MobileApp/2.1.5"),
    x_timezone: str = Header("UTC", alias="X-Timezone", example="Asia/Ho_Chi_Minh"),
    x_language: str = Header("en", alias="X-Language", example="vi"),
    
    # Query parameters
    update_inventory: bool = Query(True, description="Whether to update inventory levels", example=True),
    notify_supplier: bool = Query(False, description="Send notification to supplier", example=False),
    priority: str = Query("normal", description="Update priority level", example="high"),
    batch_id: Optional[str] = Query(None, description="Batch update identifier", example="BATCH_20240115_001"),
    dry_run: bool = Query(False, description="Simulate update without making changes", example=False),
    
    # Additional query parameters
    include_analytics: bool = Query(True, description="Include analytics data in response", example=True),
    return_previous_state: bool = Query(False, description="Return previous product state", example=False),
    validate_only: bool = Query(False, description="Validate data without updating", example=False)
):
    """
    Testing API 3 - PUT method with comprehensive parameters
    Simulates a product update endpoint with extensive configuration options
    """
    try:
        # Simulate merchant validation
        if len(x_merchant_key) < 10:
            raise HTTPException(status_code=403, detail="Invalid merchant key")
        
        # Validate priority
        valid_priorities = ["low", "normal", "high", "urgent"]
        if priority not in valid_priorities:
            raise HTTPException(status_code=400, detail=f"Invalid priority. Must be one of: {valid_priorities}")
        
        # Simulate dry run mode
        if dry_run:
            return ApiResponse(
                success=True,
                message="Dry run completed - no changes made",
                data={
                    "dry_run": True,
                    "would_update": {
                        "product_id": product_info.product_id,
                        "changes": "Product would be updated with provided data"
                    }
                },
                timestamp=datetime.now().isoformat()
            )
        
        # Validate only mode
        if validate_only:
            return ApiResponse(
                success=True,
                message="Validation completed successfully",
                data={
                    "validation": {
                        "product_id": product_info.product_id,
                        "is_valid": True,
                        "warnings": []
                    }
                },
                timestamp=datetime.now().isoformat()
            )
        
        # Fake product update response
        response_data = {
            "updated_product": {
                "product_id": product_info.product_id,
                "name": product_info.name,
                "price": product_info.price,
                "category": product_info.category,
                "in_stock": product_info.in_stock,
                "description": product_info.description,
                "tags": product_info.tags,
                "weight": product_info.weight,
                "dimensions": product_info.dimensions,
                "supplier_info": product_info.supplier_info,
                "last_updated": datetime.now().isoformat(),
                "store_id": x_store_id,
                "sku": f"SKU-{product_info.product_id}-{x_store_id}",
                "status": "updated",
                "update_priority": priority,
                "batch_id": batch_id
            },
            "inventory_status": {
                "stock_level": 150 if product_info.in_stock else 0,
                "reorder_point": 20,
                "last_restocked": "2024-01-10T09:00:00Z",
                "inventory_updated": update_inventory
            },
            "request_info": {
                "store_id": x_store_id,
                "merchant_key_length": len(x_merchant_key),
                "accept_header": accept,
                "request_method": "PUT",
                "client_version": x_client_version,
                "request_id": x_request_id,
                "user_agent": x_user_agent,
                "timezone": x_timezone,
                "language": x_language,
                "update_inventory": update_inventory,
                "notify_supplier": notify_supplier,
                "priority": priority,
                "batch_id": batch_id,
                "dry_run": dry_run,
                "include_analytics": include_analytics,
                "return_previous_state": return_previous_state,
                "validate_only": validate_only
            }
        }
        
        # Add analytics if requested
        if include_analytics:
            response_data["analytics"] = {
                "update_frequency": "daily",
                "last_30_days_updates": 15,
                "popular_categories": ["Electronics", "Fashion", "Home"],
                "price_change_trend": "stable"
            }
        
        # Add previous state if requested
        if return_previous_state:
            response_data["previous_state"] = {
                "product_id": product_info.product_id,
                "name": f"Previous {product_info.name}",
                "price": product_info.price * 0.95,
                "last_updated": "2024-01-14T10:00:00Z"
            }
        
        return ApiResponse(
            success=True,
            message="Product updated successfully",
            data=response_data,
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in api_3: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/api_4")
async def api_4(
    order_data: OrderRequest = Body(...),
    x_admin_token: str = Header(..., alias="X-Admin-Token", example="admin_secret_token_123"),
    x_reason_code: str = Header(None, alias="X-Reason-Code", example="CUSTOMER_REQUEST"),
    if_match: str = Header(None, alias="If-Match", example="etag-ORD_20240115_001"),
    x_audit_user: str = Header("system", alias="X-Audit-User", example="admin_user_001")
):
    """
    Testing API 4 - DELETE method with body and admin headers
    Simulates an order cancellation endpoint
    """
    try:
        # Simulate admin token validation
        if x_admin_token != "admin_secret_token_123":
            raise HTTPException(status_code=403, detail="Insufficient privileges")
        
        # Simulate conditional deletion with If-Match
        if if_match and if_match != f"etag-{order_data.order_id}":
            raise HTTPException(status_code=412, detail="Precondition failed - order was modified")
        
        # Fake order cancellation response
        response_data = {
            "cancelled_order": {
                "order_id": order_data.order_id,
                "original_amount": order_data.total_amount,
                "refund_amount": order_data.total_amount * 0.95,  # 5% cancellation fee
                "items_count": len(order_data.items),
                "customer_email": order_data.customer_info.get("email", "unknown"),
                "cancellation_timestamp": datetime.now().isoformat(),
                "status": "cancelled",
                "reason_code": x_reason_code or "user_requested"
            },
            "refund_info": {
                "refund_id": f"ref_{order_data.order_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "processing_time": "3-5 business days",
                "refund_method": "original_payment_method"
            },
            "audit_trail": {
                "cancelled_by": x_audit_user,
                "admin_token_used": True,
                "reason_code": x_reason_code or "not_specified",
                "if_match_header": if_match or "not_provided"
            }
        }
        
        return ApiResponse(
            success=True,
            message="Order cancelled successfully",
            data=response_data,
            timestamp=datetime.now().isoformat()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in api_4: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/test-summary")
async def get_test_summary():
    """
    Get summary of all testing APIs available
    """
    return {
        "testing_apis": {
            "api_1": {
                "method": "GET",
                "path": "/api/testing/api_1",
                "description": "User profile retrieval with custom headers",
                "headers": ["X-API-Key", "X-Request-ID", "User-Agent"],
                "response_type": "user_profile_data"
            },
            "api_2": {
                "method": "POST", 
                "path": "/api/testing/api_2",
                "description": "User registration with JSON body and auth",
                "headers": ["Authorization", "Content-Type", "X-Client-Version"],
                "body_type": "UserData",
                "response_type": "created_user_data"
            },
            "api_3": {
                "method": "PUT",
                "path": "/api/testing/api_3", 
                "description": "Product update with required merchant headers",
                "headers": ["X-Store-ID", "X-Merchant-Key", "Accept"],
                "body_type": "ProductInfo",
                "response_type": "updated_product_data"
            },
            "api_4": {
                "method": "DELETE",
                "path": "/api/testing/api_4",
                "description": "Order cancellation with admin privileges and body",
                "headers": ["X-Admin-Token", "X-Reason-Code", "If-Match", "X-Audit-User"],
                "body_type": "OrderRequest", 
                "response_type": "cancelled_order_data"
            },
            "inventory": {
                "method": "GET",
                "path": "/api/testing/inventory",
                "description": "Get inventory list with warehouse headers",
                "headers": ["X-Warehouse-ID", "X-Manager-Token", "X-Include-OutOfStock"],
                "response_type": "product_list_data"
            }
        },
        "note": "These APIs are designed for testing URL import functionality with diverse patterns"
    }


@router.get("/inventory")
async def get_inventory(
    request: Request,
    x_warehouse_id: str = Header(..., alias="X-Warehouse-ID", example="WH_HCM_001"),
    x_manager_token: str = Header(..., alias="X-Manager-Token", example="manager_token_abc123"),
    x_include_out_of_stock: str = Header("false", alias="X-Include-OutOfStock", example="true"),
    category: Optional[str] = Query(None, example="Electronics", description="Filter by product category"),
    min_price: Optional[float] = Query(None, example=1000000.0, description="Minimum price filter"),
    max_price: Optional[float] = Query(None, example=50000000.0, description="Maximum price filter")
):
    """
    Testing API - Inventory Management
    GET method for retrieving product inventory list
    Simulates a warehouse inventory system
    """
    try:
        # Validate manager token
        if x_manager_token != "manager_token_abc123":
            raise HTTPException(status_code=403, detail="Invalid manager token")
        
        # Validate warehouse ID
        valid_warehouses = ["WH_HCM_001", "WH_HN_002", "WH_DN_003"]
        if x_warehouse_id not in valid_warehouses:
            raise HTTPException(status_code=404, detail="Warehouse not found")
        
        # Generate fake product inventory
        include_out_of_stock = x_include_out_of_stock.lower() == "true"
        
        all_products = [
            {
                "product_id": "prod_001",
                "sku": f"SKU-001-{x_warehouse_id}",
                "name": "iPhone 15 Pro Max",
                "category": "Electronics",
                "price": 29990000.0,
                "currency": "VND",
                "stock_quantity": 45,
                "reserved_quantity": 5,
                "available_quantity": 40,
                "warehouse_location": "A1-B2-C3",
                "last_updated": "2024-01-15T08:30:00Z",
                "supplier": "Apple Vietnam",
                "cost_price": 25000000.0,
                "margin_percent": 19.96
            },
            {
                "product_id": "prod_002",
                "sku": f"SKU-002-{x_warehouse_id}",
                "name": "AirPods Pro",
                "category": "Electronics",
                "price": 6490000.0,
                "currency": "VND",
                "stock_quantity": 120,
                "reserved_quantity": 10,
                "available_quantity": 110,
                "warehouse_location": "A2-B1-C5",
                "last_updated": "2024-01-15T09:15:00Z",
                "supplier": "Apple Vietnam",
                "cost_price": 5200000.0,
                "margin_percent": 24.84
            },
            {
                "product_id": "prod_003",
                "sku": f"SKU-003-{x_warehouse_id}",
                "name": "Samsung Galaxy S24 Ultra",
                "category": "Electronics",
                "price": 32990000.0,
                "currency": "VND",
                "stock_quantity": 0,
                "reserved_quantity": 0,
                "available_quantity": 0,
                "warehouse_location": "A1-B3-C1",
                "last_updated": "2024-01-14T16:45:00Z",
                "supplier": "Samsung Vietnam",
                "cost_price": 28000000.0,
                "margin_percent": 17.82,
                "status": "out_of_stock",
                "expected_restock": "2024-01-20T00:00:00Z"
            },
            {
                "product_id": "prod_004",
                "sku": f"SKU-004-{x_warehouse_id}",
                "name": "MacBook Pro 14 inch M3",
                "category": "Computers",
                "price": 54990000.0,
                "currency": "VND",
                "stock_quantity": 15,
                "reserved_quantity": 2,
                "available_quantity": 13,
                "warehouse_location": "B1-C2-D1",
                "last_updated": "2024-01-15T07:20:00Z",
                "supplier": "Apple Vietnam",
                "cost_price": 46000000.0,
                "margin_percent": 19.54
            },
            {
                "product_id": "prod_005",
                "sku": f"SKU-005-{x_warehouse_id}",
                "name": "Dell XPS 13 Plus",
                "category": "Computers",
                "price": 35990000.0,
                "currency": "VND",
                "stock_quantity": 0,
                "reserved_quantity": 0,
                "available_quantity": 0,
                "warehouse_location": "B2-C1-D3",
                "last_updated": "2024-01-13T14:30:00Z",
                "supplier": "Dell Vietnam",
                "cost_price": 30000000.0,
                "margin_percent": 19.97,
                "status": "out_of_stock",
                "expected_restock": "2024-01-25T00:00:00Z"
            }
        ]
        
        # Filter products based on parameters
        filtered_products = all_products
        
        # Filter by category
        if category:
            filtered_products = [p for p in filtered_products if p["category"].lower() == category.lower()]
        
        # Filter by price range
        if min_price is not None:
            filtered_products = [p for p in filtered_products if p["price"] >= min_price]
        if max_price is not None:
            filtered_products = [p for p in filtered_products if p["price"] <= max_price]
        
        # Filter out of stock products if not requested
        if not include_out_of_stock:
            filtered_products = [p for p in filtered_products if p["available_quantity"] > 0]
        
        # Calculate inventory statistics
        total_products = len(filtered_products)
        total_stock_value = sum(p["stock_quantity"] * p["cost_price"] for p in filtered_products)
        out_of_stock_count = len([p for p in filtered_products if p["available_quantity"] == 0])
        low_stock_count = len([p for p in filtered_products if 0 < p["available_quantity"] <= 10])
        
        response_data = {
            "inventory_summary": {
                "warehouse_id": x_warehouse_id,
                "total_products": total_products,
                "out_of_stock_products": out_of_stock_count,
                "low_stock_products": low_stock_count,
                "total_stock_value": total_stock_value,
                "currency": "VND",
                "last_sync": datetime.now().isoformat()
            },
            "products": filtered_products,
            "filters_applied": {
                "category": category,
                "min_price": min_price,
                "max_price": max_price,
                "include_out_of_stock": include_out_of_stock
            },
            "request_info": {
                "warehouse_id": x_warehouse_id,
                "manager_token_valid": True,
                "request_timestamp": datetime.now().isoformat()
            }
        }
        
        return ApiResponse(
            success=True,
            message=f"Inventory retrieved successfully for warehouse {x_warehouse_id}",
            data=response_data,
            timestamp=datetime.now().isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in inventory API: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 