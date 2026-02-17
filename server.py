#!/usr/bin/env python3
"""
Coinmarketcap API MCP Server - FastMCP with D402 Transport Wrapper

Uses FastMCP from official MCP SDK with D402MCPTransport wrapper for HTTP 402.

Architecture:
- FastMCP for tool decorators and Context objects
- D402MCPTransport wraps the /mcp route for HTTP 402 interception
- Proper HTTP 402 status codes (not JSON-RPC wrapped)

Generated from OpenAPI: https://coinmarketcap.com/api/documentation/v1/

Environment Variables:
- COINMARKETCAP_API_KEY: Server's internal API key (for paid requests)
- SERVER_ADDRESS: Payment address (IATP wallet contract)
- MCP_OPERATOR_PRIVATE_KEY: Operator signing key
- D402_TESTING_MODE: Skip facilitator (default: true)
"""

import os
import logging
import sys
from typing import Any, Callable, Dict, List, Optional, Sequence, Set, Tuple, Union
from datetime import datetime

import requests
from retry import retry
from dotenv import load_dotenv
import uvicorn

load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO").upper(),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('coinmarketcap-api_mcp')

# FastMCP from official SDK
from mcp.server.fastmcp import FastMCP, Context
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.middleware.cors import CORSMiddleware

# D402 payment protocol - using Starlette middleware
from traia_iatp.d402.starlette_middleware import D402PaymentMiddleware
from traia_iatp.d402.mcp_middleware import require_payment_for_tool, get_active_api_key
from traia_iatp.d402.payment_introspection import extract_payment_configs_from_mcp
from traia_iatp.d402.types import TokenAmount, TokenAsset, EIP712Domain

# Configuration
STAGE = os.getenv("STAGE", "MAINNET").upper()
PORT = int(os.getenv("PORT", "8000"))
SERVER_ADDRESS = os.getenv("SERVER_ADDRESS")
if not SERVER_ADDRESS:
    raise ValueError("SERVER_ADDRESS required for payment protocol")

API_KEY = os.getenv("COINMARKETCAP_API_KEY")
if not API_KEY:
    logger.warning(f"⚠️  COINMARKETCAP_API_KEY not set - payment required for all requests")

logger.info("="*80)
logger.info(f"Coinmarketcap API MCP Server (FastMCP + D402 Wrapper)")
logger.info(f"API: https://pro-api.coinmarketcap.com/")
logger.info(f"Payment: {SERVER_ADDRESS}")
logger.info(f"API Key: {'✅' if API_KEY else '❌ Payment required'}")
logger.info("="*80)

# Create FastMCP server
mcp = FastMCP("Coinmarketcap API MCP Server", host="0.0.0.0")

logger.info(f"✅ FastMCP server created")

# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================
# Tool implementations will be added here by endpoint_implementer_crew
# Each tool will use the @mcp.tool() and @require_payment_for_tool() decorators


# D402 Payment Middleware
# The HTTP 402 payment protocol middleware is already configured in the server initialization.
# It's imported from traia_iatp.d402.mcp_middleware and auto-detects configuration from:
# - PAYMENT_ADDRESS or EVM_ADDRESS: Where to receive payments
# - EVM_NETWORK: Blockchain network (default: base-sepolia)
# - DEFAULT_PRICE_USD: Price per request (default: $0.001)
# - COINMARKETCAP_API_API_KEY: Server's internal API key for payment mode
#
# All payment verification logic is handled by the traia_iatp.d402 module.
# No custom implementation needed!


# API Endpoint Tool Implementations

@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns a list of past, present, or future airdrop"

)
async def airdrops(
    context: Context,
    start: int = 1,
    limit: int = 100,
    status: str = "ONGOING",
    id: Optional[str] = None,
    slug: Optional[str] = None,
    symbol: Optional[str] = None
) -> Any:
    """
    Returns a list of past, present, or future airdrops which have run on CoinMarketCap. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Hobbyist - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** Data is updated only as needed, every 30 seconds. **Plan credit use:** 1 API call credit per request no matter query size. **CMC equivalent pages:** Our free airdrops page [coinmarketcap.com/airdrop/](https://coinmarketcap.com/airdrop/).

    Generated from OpenAPI endpoint: GET /v1/cryptocurrency/airdrops

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        start: Optionally offset the start (1-based index) of the paginated list of items to return. (optional, default: 1)
        limit: Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size. (optional, default: 100)
        status: What status of airdrops. (optional, default: "ONGOING")
        id: Filtered airdrops by one cryptocurrency CoinMarketCap IDs. Example: 1 (optional) Examples: "1"
        slug: Alternatively filter airdrops by a cryptocurrency slug. Example: "bitcoin" (optional) Examples: "bitcoin"
        symbol: Alternatively filter airdrops one cryptocurrency symbol. Example: "BTC". (optional) Examples: "BTC"

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await airdrops()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/airdrops"
        params = {
            "start": start,
            "limit": limit,
            "status": status,
            "id": id,
            "slug": slug,
            "symbol": symbol
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in airdrops: {e}")
        return {"error": str(e), "endpoint": "/v1/cryptocurrency/airdrops"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns information about all coin categories avai"

)
async def categories(
    context: Context,
    start: int = 1,
    limit: Optional[int] = None,
    id: Optional[str] = None,
    slug: Optional[str] = None,
    symbol: Optional[str] = None
) -> Any:
    """
    Returns information about all coin categories available on CoinMarketCap. Includes a paginated list of cryptocurrency quotes and metadata from each category. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Free - Hobbyist - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** Data is updated only as needed, every 30 seconds. **Plan credit use:** 1 API call credit per request + 1 call credit per 200 cryptocurrencies returned (rounded up) and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** Our free airdrops page [coinmarketcap.com/cryptocurrency-category/](https://coinmarketcap.com/cryptocurrency-category/).

    Generated from OpenAPI endpoint: GET /v1/cryptocurrency/categories

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        start: Optionally offset the start (1-based index) of the paginated list of items to return. (optional, default: 1)
        limit: Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size. (optional)
        id: Filtered categories by one or more comma-separated cryptocurrency CoinMarketCap IDs. Example: 1,2 (optional) Examples: "1", "2"
        slug: Alternatively filter categories by a comma-separated list of cryptocurrency slugs. Example: "bitcoin,ethereum" (optional) Examples: "bitcoin", "ethereum"
        symbol: Alternatively filter categories one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". (optional) Examples: "BTC", "ETH"

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await categories()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/categories"
        params = {
            "start": start,
            "limit": limit,
            "id": id,
            "slug": slug,
            "symbol": symbol
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in categories: {e}")
        return {"error": str(e), "endpoint": "/v1/cryptocurrency/categories"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns information about a single coin category a"

)
async def category(
    context: Context,
    id: str,
    start: int = 1,
    limit: int = 100,
    convert: Optional[str] = None,
    convert_id: Optional[str] = None
) -> Any:
    """
    Returns information about a single coin category available on CoinMarketCap. Includes a paginated list of the cryptocurrency quotes and metadata for the category. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Free - Hobbyist - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** Data is updated only as needed, every 30 seconds. **Plan credit use:** 1 API call credit per request + 1 call credit per 200 cryptocurrencies returned (rounded up) and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** Our Cryptocurrency Category page [coinmarketcap.com/cryptocurrency-category/](https://coinmarketcap.com/cryptocurrency-category/).

    Generated from OpenAPI endpoint: GET /v1/cryptocurrency/category

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        id: The Category ID. This can be found using the Categories API. (optional) Examples: "605e2ce9d41eae1066535f7c"
        start: Optionally offset the start (1-based index) of the paginated list of coins to return. (optional, default: 1)
        limit: Optionally specify the number of coins to return. Use this parameter and the "start" parameter to determine your own pagination size. (optional, default: 100)
        convert: Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found [here](#section/Standards-and-Conventions). Each conversion is returned in its own "quote" object. (optional)
        convert_id: Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await category(id="605e2ce9d41eae1066535f7c")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/category"
        params = {
            "id": id,
            "start": start,
            "limit": limit,
            "convert": convert,
            "convert_id": convert_id
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in category: {e}")
        return {"error": str(e), "endpoint": "/v1/cryptocurrency/category"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns a ranked and sorted list of all cryptocurr"

)
async def listings_historical(
    context: Context,
    date: str,
    start: int = 1,
    limit: int = 100,
    convert: Optional[str] = None,
    convert_id: Optional[str] = None,
    sort: str = "cmc_rank",
    sort_dir: Optional[str] = None,
    cryptocurrency_type: str = "all",
    aux: str = "platform,tags,date_added,circulating_supply,total_supply,max_supply,cmc_rank,num_market_pairs"
) -> Any:
    """
    Returns a ranked and sorted list of all cryptocurrencies for a historical UTC date. **Technical Notes** - This endpoint is identical in format to our [/cryptocurrency/listings/latest](#operation/getV1CryptocurrencyListingsLatest) endpoint but is used to retrieve historical daily ranking snapshots from the end of each UTC day. - Daily snapshots reflect market data at the end of each UTC day and may be requested as far back as 2013-04-28 (as supported by your plan's historical limits). - The required "date" parameter can be passed as a Unix timestamp or ISO 8601 date but only the date portion of the timestamp will be referenced. It is recommended to send an ISO date format like "2019-10-10" without time. - This endpoint is for retrieving paginated and sorted lists of all currencies. If you require historical market data on specific cryptocurrencies you should use [/cryptocurrency/quotes/historical](#operation/getV1CryptocurrencyQuotesHistorical). Cryptocurrencies are listed by cmc_rank by default. You may optionally sort against any of the following: **cmc_rank**: CoinMarketCap's market cap rank as outlined in <a href="https://coinmarketcap.com/methodology/" target="_blank">our methodology</a>. **name**: The cryptocurrency name. **symbol**: The cryptocurrency symbol. **market_cap**: market cap (latest trade price x circulating supply). **price**: latest average trade price across markets. **circulating_supply**: approximate number of coins currently in circulation. **total_supply**: approximate total amount of coins in existence right now (minus any coins that have been verifiably burned). **max_supply**: our best approximation of the maximum amount of coins that will ever exist in the lifetime of the currency. **num_market_pairs**: number of market pairs across all exchanges trading each currency. **volume_24h**: 24 hour trading volume for each currency. **percent_change_1h**: 1 hour trading price percentage change for each currency. **percent_change_24h**: 24 hour trading price percentage change for each currency. **percent_change_7d**: 7 day trading price percentage change for each currency. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - ~~Basic~~ - Hobbyist (1 month) - Startup (1 month) - Standard (3 month) - Professional (12 months) - Enterprise (Up to 6 years) **Cache / Update frequency:** The last completed UTC day is available 30 minutes after midnight on the next UTC day. **Plan credit use:** 1 call credit per 100 cryptocurrencies returned (rounded up) and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** Our historical daily crypto ranking snapshot pages like this one on [February 02, 2014](https://coinmarketcap.com/historical/20140202/).

    Generated from OpenAPI endpoint: GET /v1/cryptocurrency/listings/historical

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        date: date (Unix or ISO 8601) to reference day of snapshot. (optional) Examples: "2026-02-01"
        start: Optionally offset the start (1-based index) of the paginated list of items to return. (optional, default: 1)
        limit: Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size. (optional, default: 100)
        convert: Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found [here](#section/Standards-and-Conventions). Each conversion is returned in its own "quote" object. (optional)
        convert_id: Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)
        sort: What field to sort the list of cryptocurrencies by. (optional, default: "cmc_rank")
        sort_dir: The direction in which to order cryptocurrencies against the specified sort. (optional)
        cryptocurrency_type: The type of cryptocurrency to include. (optional, default: "all")
        aux: Optionally specify a comma-separated list of supplemental data fields to return. Pass `platform,tags,date_added,circulating_supply,total_supply,max_supply,cmc_rank,num_market_pairs` to include all auxiliary fields. (optional, default: "platform,tags,date_added,circulating_supply,total_supply,max_supply,cmc_rank,num_market_pairs")

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await listings_historical(date="2026-02-01")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/historical"
        params = {
            "date": date,
            "start": start,
            "limit": limit,
            "convert": convert,
            "convert_id": convert_id,
            "sort": sort,
            "sort_dir": sort_dir,
            "cryptocurrency_type": cryptocurrency_type,
            "aux": aux
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in listings_historical: {e}")
        return {"error": str(e), "endpoint": "/v1/cryptocurrency/listings/historical"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns a paginated list of all active cryptocurre"

)
async def listings_latest(
    context: Context,
    start: int = 1,
    limit: int = 100,
    price_min: Optional[float] = None,
    price_max: Optional[float] = None,
    market_cap_min: Optional[float] = None,
    market_cap_max: Optional[float] = None,
    volume_24h_min: Optional[float] = None,
    volume_24h_max: Optional[float] = None,
    circulating_supply_min: Optional[float] = None,
    circulating_supply_max: Optional[float] = None,
    percent_change_24h_min: Optional[float] = None,
    percent_change_24h_max: Optional[float] = None,
    self_reported_circulating_supply_min: Optional[float] = None,
    self_reported_circulating_supply_max: Optional[float] = None,
    self_reported_market_cap_min: Optional[float] = None,
    self_reported_market_cap_max: Optional[float] = None,
    unlocked_market_cap_min: Optional[float] = None,
    unlocked_market_cap_max: Optional[float] = None,
    unlocked_circulating_supply_min: Optional[float] = None,
    unlocked_circulating_supply_max: Optional[float] = None,
    convert: Optional[str] = None,
    convert_id: Optional[str] = None,
    sort: str = "market_cap",
    sort_dir: Optional[str] = None,
    cryptocurrency_type: str = "all",
    tag: str = "all",
    aux: str = "num_market_pairs,cmc_rank,date_added,tags,platform,max_supply,circulating_supply,total_supply"
) -> Any:
    """
    Returns a paginated list of all active cryptocurrencies with latest market data. The default "market_cap" sort returns cryptocurrency in order of CoinMarketCap's market cap rank (as outlined in <a href="https://coinmarketcap.com/methodology/" target="_blank">our methodology</a>) but you may configure this call to order by another market ranking field. Use the "convert" option to return market values in multiple fiat and cryptocurrency conversions in the same call. You may sort against any of the following: **market_cap**: CoinMarketCap's market cap rank as outlined in <a href="https://coinmarketcap.com/methodology/" target="_blank">our methodology</a>. **market_cap_strict**: A strict market cap sort (latest trade price x circulating supply). **name**: The cryptocurrency name. **symbol**: The cryptocurrency symbol. **date_added**: Date cryptocurrency was added to the system. **price**: latest average trade price across markets. **circulating_supply**: approximate number of coins currently in circulation. **total_supply**: approximate total amount of coins in existence right now (minus any coins that have been verifiably burned). **max_supply**: our best approximation of the maximum amount of coins that will ever exist in the lifetime of the currency. **num_market_pairs**: number of market pairs across all exchanges trading each currency. **market_cap_by_total_supply_strict**: market cap by total supply. **volume_24h**: rolling 24 hour adjusted trading volume. **volume_7d**: rolling 24 hour adjusted trading volume. **volume_30d**: rolling 24 hour adjusted trading volume. **percent_change_1h**: 1 hour trading price percentage change for each currency. **percent_change_24h**: 24 hour trading price percentage change for each currency. **percent_change_7d**: 7 day trading price percentage change for each currency. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Basic - Hobbyist - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** Every 60 seconds. **Plan credit use:** 1 call credit per 200 cryptocurrencies returned (rounded up) and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** Our latest cryptocurrency listing and ranking pages like [coinmarketcap.com/all/views/all/](https://coinmarketcap.com/all/views/all/), [coinmarketcap.com/tokens/](https://coinmarketcap.com/tokens/), [coinmarketcap.com/gainers-losers/](https://coinmarketcap.com/gainers-losers/), [coinmarketcap.com/new/](https://coinmarketcap.com/new/). ***NOTE:** Use this endpoint if you need a sorted and paginated list of all cryptocurrencies. If you want to query for market data on a few specific cryptocurrencies use [/v1/cryptocurrency/quotes/latest](#operation/getV1CryptocurrencyQuotesLatest) which is optimized for that purpose. The response data between these endpoints is otherwise the same.*

    Generated from OpenAPI endpoint: GET /v1/cryptocurrency/listings/latest

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        start: Optionally offset the start (1-based index) of the paginated list of items to return. (optional, default: 1)
        limit: Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size. (optional, default: 100)
        price_min: Optionally specify a threshold of minimum USD price to filter results by. (optional)
        price_max: Optionally specify a threshold of maximum USD price to filter results by. (optional)
        market_cap_min: Optionally specify a threshold of minimum market cap to filter results by. (optional)
        market_cap_max: Optionally specify a threshold of maximum market cap to filter results by. (optional)
        volume_24h_min: Optionally specify a threshold of minimum 24 hour USD volume to filter results by. (optional)
        volume_24h_max: Optionally specify a threshold of maximum 24 hour USD volume to filter results by. (optional)
        circulating_supply_min: Optionally specify a threshold of minimum circulating supply to filter results by. (optional)
        circulating_supply_max: Optionally specify a threshold of maximum circulating supply to filter results by. (optional)
        percent_change_24h_min: Optionally specify a threshold of minimum 24 hour percent change to filter results by. (optional)
        percent_change_24h_max: Optionally specify a threshold of maximum 24 hour percent change to filter results by. (optional)
        self_reported_circulating_supply_min: Optionally specify a threshold of minimum self reported circulating supply to filter results by. (optional)
        self_reported_circulating_supply_max: Optionally specify a threshold of maximum self reported circulating supply to filter results by. (optional)
        self_reported_market_cap_min: Optionally specify a threshold of minimum self reported market cap to filter results by. (optional)
        self_reported_market_cap_max: Optionally specify a threshold of maximum self reported market cap to filter results by. (optional)
        unlocked_market_cap_min: Optionally specify a threshold of minimum unlocked market cap to filter results by. (optional)
        unlocked_market_cap_max: Optionally specify a threshold of maximum unlocked market cap to filter results by. (optional)
        unlocked_circulating_supply_min: Optionally specify a threshold of minimum unlocked circulating supply to filter results by. (optional)
        unlocked_circulating_supply_max: Optionally specify a threshold of maximum unlocked circulating supply to filter results by. (optional)
        convert: Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found [here](#section/Standards-and-Conventions). Each conversion is returned in its own "quote" object. (optional)
        convert_id: Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)
        sort: What field to sort the list of cryptocurrencies by. (optional, default: "market_cap")
        sort_dir: The direction in which to order cryptocurrencies against the specified sort. (optional)
        cryptocurrency_type: The type of cryptocurrency to include. (optional, default: "all")
        tag: The tag of cryptocurrency to include. (optional, default: "all")
        aux: Optionally specify a comma-separated list of supplemental data fields to return. Pass `num_market_pairs,cmc_rank,date_added,tags,platform,max_supply,circulating_supply,total_supply,market_cap_by_total_supply,volume_24h_reported,volume_7d,volume_7d_reported,volume_30d,volume_30d_reported,is_market_cap_included_in_calc` to include all auxiliary fields. (optional, default: "num_market_pairs,cmc_rank,date_added,tags,platform,max_supply,circulating_supply,total_supply")

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await listings_latest()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/latest"
        params = {
            "start": start,
            "limit": limit,
            "price_min": price_min,
            "price_max": price_max,
            "market_cap_min": market_cap_min,
            "market_cap_max": market_cap_max,
            "volume_24h_min": volume_24h_min,
            "volume_24h_max": volume_24h_max,
            "circulating_supply_min": circulating_supply_min,
            "circulating_supply_max": circulating_supply_max,
            "percent_change_24h_min": percent_change_24h_min,
            "percent_change_24h_max": percent_change_24h_max,
            "self_reported_circulating_supply_min": self_reported_circulating_supply_min,
            "self_reported_circulating_supply_max": self_reported_circulating_supply_max,
            "self_reported_market_cap_min": self_reported_market_cap_min,
            "self_reported_market_cap_max": self_reported_market_cap_max,
            "unlocked_market_cap_min": unlocked_market_cap_min,
            "unlocked_market_cap_max": unlocked_market_cap_max,
            "unlocked_circulating_supply_min": unlocked_circulating_supply_min,
            "unlocked_circulating_supply_max": unlocked_circulating_supply_max,
            "convert": convert,
            "convert_id": convert_id,
            "sort": sort,
            "sort_dir": sort_dir,
            "cryptocurrency_type": cryptocurrency_type,
            "tag": tag,
            "aux": aux
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in listings_latest: {e}")
        return {"error": str(e), "endpoint": "/v1/cryptocurrency/listings/latest"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns a paginated list of most recently added cr"

)
async def listings_new(
    context: Context,
    start: int = 1,
    limit: int = 100,
    convert: Optional[str] = None,
    convert_id: Optional[str] = None,
    sort_dir: Optional[str] = None
) -> Any:
    """
    Returns a paginated list of most recently added cryptocurrencies. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** Every 60 seconds. **Plan credit use:** 1 call credit per 200 cryptocurrencies returned (rounded up) and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** Our "new" cryptocurrency page [coinmarketcap.com/new/](https://coinmarketcap.com/new) ***NOTE:** Use this endpoint if you need a sorted and paginated list of all recently added cryptocurrencies.*

    Generated from OpenAPI endpoint: GET /v1/cryptocurrency/listings/new

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        start: Optionally offset the start (1-based index) of the paginated list of items to return. (optional, default: 1)
        limit: Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size. (optional, default: 100)
        convert: Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found [here](#section/Standards-and-Conventions). Each conversion is returned in its own "quote" object. (optional)
        convert_id: Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)
        sort_dir: The direction in which to order cryptocurrencies against the specified sort. (optional)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await listings_new()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/listings/new"
        params = {
            "start": start,
            "limit": limit,
            "convert": convert,
            "convert_id": convert_id,
            "sort_dir": sort_dir
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in listings_new: {e}")
        return {"error": str(e), "endpoint": "/v1/cryptocurrency/listings/new"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns a mapping of all cryptocurrencies to uniqu"

)
async def coinmarketcap_id_map(
    context: Context,
    listing_status: str = "active",
    start: int = 1,
    limit: Optional[int] = None,
    sort: str = "id",
    symbol: Optional[str] = None,
    aux: str = "platform,first_historical_data,last_historical_data,is_active"
) -> Any:
    """
    Returns a mapping of all cryptocurrencies to unique CoinMarketCap `id`s. Per our <a href="#section/Best-Practices" target="_blank">Best Practices</a> we recommend utilizing CMC ID instead of cryptocurrency symbols to securely identify cryptocurrencies with our other endpoints and in your own application logic. Each cryptocurrency returned includes typical identifiers such as `name`, `symbol`, and `token_address` for flexible mapping to `id`. By default this endpoint returns cryptocurrencies that have actively tracked markets on supported exchanges. You may receive a map of all inactive cryptocurrencies by passing `listing_status=inactive`. You may also receive a map of registered cryptocurrency projects that are listed but do not yet meet methodology requirements to have tracked markets via `listing_status=untracked`. Please review our <a target="_blank" href="https://coinmarketcap.com/methodology/">methodology documentation</a> for additional details on listing states. Cryptocurrencies returned include `first_historical_data` and `last_historical_data` timestamps to conveniently reference historical date ranges available to query with historical time-series data endpoints. You may also use the `aux` parameter to only include properties you require to slim down the payload if calling this endpoint frequently. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Basic - Hobbyist - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** Mapping data is updated only as needed, every 30 seconds. **Plan credit use:** 1 API call credit per request no matter query size. **CMC equivalent pages:** No equivalent, this data is only available via API.

    Generated from OpenAPI endpoint: GET /v1/cryptocurrency/map

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        listing_status: Only active cryptocurrencies are returned by default. Pass `inactive` to get a list of cryptocurrencies that are no longer active. Pass `untracked` to get a list of cryptocurrencies that are listed but do not yet meet methodology requirements to have tracked markets available. You may pass one or more comma-separated values. (optional, default: "active")
        start: Optionally offset the start (1-based index) of the paginated list of items to return. (optional, default: 1)
        limit: Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size. (optional)
        sort: What field to sort the list of cryptocurrencies by. (optional, default: "id")
        symbol: Optionally pass a comma-separated list of cryptocurrency symbols to return CoinMarketCap IDs for. If this option is passed, other options will be ignored. (optional)
        aux: Optionally specify a comma-separated list of supplemental data fields to return. Pass `platform,first_historical_data,last_historical_data,is_active,status` to include all auxiliary fields. (optional, default: "platform,first_historical_data,last_historical_data,is_active")

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await coinmarketcap_id_map()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/map"
        params = {
            "listing_status": listing_status,
            "start": start,
            "limit": limit,
            "sort": sort,
            "symbol": symbol,
            "aux": aux
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in coinmarketcap_id_map: {e}")
        return {"error": str(e), "endpoint": "/v1/cryptocurrency/map"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns a paginated list of all trending cryptocur"

)
async def trending_gainers_losers(
    context: Context,
    start: int = 1,
    limit: int = 100,
    time_period: str = "24h",
    convert: Optional[str] = None,
    convert_id: Optional[str] = None,
    sort: str = "percent_change_24h",
    sort_dir: Optional[str] = None
) -> Any:
    """
    Returns a paginated list of all trending cryptocurrencies, determined and sorted by the largest price gains or losses. You may sort against any of the following: **percent_change_24h**: 24 hour trading price percentage change for each currency. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** Every 10 minutes. **Plan credit use:** 1 call credit per 200 cryptocurrencies returned (rounded up) and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** Our cryptocurrency Gainers & Losers page [coinmarketcap.com/gainers-losers/](https://coinmarketcap.com/gainers-losers/).

    Generated from OpenAPI endpoint: GET /v1/cryptocurrency/trending/gainers-losers

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        start: Optionally offset the start (1-based index) of the paginated list of items to return. (optional, default: 1)
        limit: Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size. (optional, default: 100)
        time_period: Adjusts the overall window of time for the biggest gainers and losers. (optional, default: "24h")
        convert: Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found [here](#section/Standards-and-Conventions). Each conversion is returned in its own "quote" object. (optional)
        convert_id: Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)
        sort: What field to sort the list of cryptocurrencies by. (optional, default: "percent_change_24h")
        sort_dir: The direction in which to order cryptocurrencies against the specified sort. (optional)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await trending_gainers_losers()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/trending/gainers-losers"
        params = {
            "start": start,
            "limit": limit,
            "time_period": time_period,
            "convert": convert,
            "convert_id": convert_id,
            "sort": sort,
            "sort_dir": sort_dir
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in trending_gainers_losers: {e}")
        return {"error": str(e), "endpoint": "/v1/cryptocurrency/trending/gainers-losers"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns a paginated list of all trending cryptocur"

)
async def trending_latest(
    context: Context,
    start: int = 1,
    limit: int = 100,
    time_period: str = "24h",
    convert: Optional[str] = None,
    convert_id: Optional[str] = None
) -> Any:
    """
    Returns a paginated list of all trending cryptocurrency market data, determined and sorted by CoinMarketCap search volume. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** Every 10 minutes. **Plan credit use:** 1 call credit per 200 cryptocurrencies returned (rounded up) and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** Our cryptocurrency Trending page [coinmarketcap.com/trending-cryptocurrencies/](https://coinmarketcap.com/trending-cryptocurrencies/).

    Generated from OpenAPI endpoint: GET /v1/cryptocurrency/trending/latest

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        start: Optionally offset the start (1-based index) of the paginated list of items to return. (optional, default: 1)
        limit: Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size. (optional, default: 100)
        time_period: Adjusts the overall window of time for the latest trending coins. (optional, default: "24h")
        convert: Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found [here](#section/Standards-and-Conventions). Each conversion is returned in its own "quote" object. (optional)
        convert_id: Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await trending_latest()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/trending/latest"
        params = {
            "start": start,
            "limit": limit,
            "time_period": time_period,
            "convert": convert,
            "convert_id": convert_id
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in trending_latest: {e}")
        return {"error": str(e), "endpoint": "/v1/cryptocurrency/trending/latest"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns a paginated list of all trending cryptocur"

)
async def trending_most_visited(
    context: Context,
    start: int = 1,
    limit: int = 100,
    time_period: str = "24h",
    convert: Optional[str] = None,
    convert_id: Optional[str] = None
) -> Any:
    """
    Returns a paginated list of all trending cryptocurrency market data, determined and sorted by traffic to coin detail pages. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** Every 24 hours. **Plan credit use:** 1 call credit per 200 cryptocurrencies returned (rounded up) and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** The CoinMarketCap “Most Visited” trending list. [coinmarketcap.com/most-viewed-pages/](https://coinmarketcap.com/most-viewed-pages/).

    Generated from OpenAPI endpoint: GET /v1/cryptocurrency/trending/most-visited

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        start: Optionally offset the start (1-based index) of the paginated list of items to return. (optional, default: 1)
        limit: Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size. (optional, default: 100)
        time_period: Adjusts the overall window of time for most visited currencies. (optional, default: "24h")
        convert: Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found [here](#section/Standards-and-Conventions). Each conversion is returned in its own "quote" object. (optional)
        convert_id: Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await trending_most_visited()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/cryptocurrency/trending/most-visited"
        params = {
            "start": start,
            "limit": limit,
            "time_period": time_period,
            "convert": convert,
            "convert_id": convert_id
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in trending_most_visited: {e}")
        return {"error": str(e), "endpoint": "/v1/cryptocurrency/trending/most-visited"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns the exchange assets in the form of token h"

)
async def exchange_assets(
    context: Context,
    id: str
) -> Any:
    """
    Returns the exchange assets in the form of token holdings. This information includes details like wallet address, cryptocurrency, blockchain platform, balance, and etc. * Only wallets containing at least 100,000 USD in balance are shown * Balances from wallets might be delayed ** Disclaimer: All information and data relating to the holdings in the third-party wallet addresses are provided by the third parties to CoinMarketCap, and CoinMarketCap does not confirm or verify the accuracy or timeliness of such information and data. The information and data are provided "as is" without warranty of any kind. CoinMarketCap shall have no responsibility or liability for these third parties’ information and data or have the duty to review, confirm, verify or otherwise perform any inquiry or investigation as to the completeness, accuracy, sufficiency, integrity, reliability or timeliness of any such information or data provided. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Free - Hobbyist - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** Balance data is updated statically based on the source. Price data is updated every 5 minutes. **Plan credit use:** 1 credit. **CMC equivalent pages:** Exchange detail page like [coinmarketcap.com/exchanges/binance/](https://coinmarketcap.com/exchanges/binance/)

    Generated from OpenAPI endpoint: GET /v1/exchange/assets

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        id: A CoinMarketCap exchange ID. Example: 270 (optional) Examples: "270"

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await exchange_assets(id="270")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/exchange/assets"
        params = {
            "id": id
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in exchange_assets: {e}")
        return {"error": str(e), "endpoint": "/v1/exchange/assets"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns all static metadata for one or more exchan"

)
async def metadata(
    context: Context,
    slug: str,
    id: Optional[str] = None,
    aux: str = "urls,logo,description,date_launched,notice"
) -> Any:
    """
    Returns all static metadata for one or more exchanges. This information includes details like launch date, logo, official website URL, social links, and market fee documentation URL. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Basic - Hobbyist - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** Static data is updated only as needed, every 30 seconds. **Plan credit use:** 1 call credit per 100 exchanges returned (rounded up). **CMC equivalent pages:** Exchange detail page metadata like [coinmarketcap.com/exchanges/binance/](https://coinmarketcap.com/exchanges/binance/).

    Generated from OpenAPI endpoint: GET /v1/exchange/info

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        id: One or more comma-separated CoinMarketCap cryptocurrency exchange ids. Example: "1,2" (optional) Examples: "1", "2"
        slug: Alternatively, one or more comma-separated exchange names in URL friendly shorthand "slug" format (all lowercase, spaces replaced with hyphens). Example: "binance,gdax". At least one "id" *or* "slug" is required. (optional) Examples: "binance", "gdax"
        aux: Optionally specify a comma-separated list of supplemental data fields to return. Pass `urls,logo,description,date_launched,notice,status` to include all auxiliary fields. (optional, default: "urls,logo,description,date_launched,notice")

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await metadata(slug="binance")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/exchange/info"
        params = {
            "id": id,
            "slug": slug,
            "aux": aux
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in metadata: {e}")
        return {"error": str(e), "endpoint": "/v1/exchange/info"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns a paginated list of all active cryptocurre"

)
async def coinmarketcap_id_map_wpht(
    context: Context,
    listing_status: str = "active",
    slug: Optional[str] = None,
    start: int = 1,
    limit: Optional[int] = None,
    sort: str = "id",
    aux: str = "first_historical_data,last_historical_data,is_active",
    crypto_id: Optional[str] = None
) -> Any:
    """
    Returns a paginated list of all active cryptocurrency exchanges by CoinMarketCap ID. We recommend using this convenience endpoint to lookup and utilize our unique exchange `id` across all endpoints as typical exchange identifiers may change over time. As a convenience you may pass a comma-separated list of exchanges by `slug` to filter this list to only those you require or the `aux` parameter to slim down the payload. By default this endpoint returns exchanges that have at least 1 actively tracked market. You may receive a map of all inactive cryptocurrencies by passing `listing_status=inactive`. You may also receive a map of registered exchanges that are listed but do not yet meet methodology requirements to have tracked markets available via `listing_status=untracked`. Please review **(3) Listing Tiers** in our <a target="_blank" href="https://coinmarketcap.com/methodology/">methodology documentation</a> for additional details on listing states. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Basic - Hobbyist - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** Mapping data is updated only as needed, every 30 seconds. **Plan credit use:** 1 call credit per call. **CMC equivalent pages:** No equivalent, this data is only available via API.

    Generated from OpenAPI endpoint: GET /v1/exchange/map

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        listing_status: Only active exchanges are returned by default. Pass `inactive` to get a list of exchanges that are no longer active. Pass `untracked` to get a list of exchanges that are registered but do not currently meet methodology requirements to have active markets tracked. You may pass one or more comma-separated values. (optional, default: "active")
        slug: Optionally pass a comma-separated list of exchange slugs (lowercase URL friendly shorthand name with spaces replaced with dashes) to return CoinMarketCap IDs for. If this option is passed, other options will be ignored. (optional)
        start: Optionally offset the start (1-based index) of the paginated list of items to return. (optional, default: 1)
        limit: Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size. (optional)
        sort: What field to sort the list of exchanges by. (optional, default: "id")
        aux: Optionally specify a comma-separated list of supplemental data fields to return. Pass `first_historical_data,last_historical_data,is_active,status` to include all auxiliary fields. (optional, default: "first_historical_data,last_historical_data,is_active")
        crypto_id: Optionally include one fiat or cryptocurrency IDs to filter market pairs by. For example `?crypto_id=1` would only return exchanges that have BTC. (optional)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await coinmarketcap_id_map_wpht()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/exchange/map"
        params = {
            "listing_status": listing_status,
            "slug": slug,
            "start": start,
            "limit": limit,
            "sort": sort,
            "aux": aux,
            "crypto_id": crypto_id
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in coinmarketcap_id_map_wpht: {e}")
        return {"error": str(e), "endpoint": "/v1/exchange/map"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns an interval of historic quotes for any exc"

)
async def quotes_historical(
    context: Context,
    slug: str,
    id: Optional[str] = None,
    time_start: Optional[str] = None,
    time_end: Optional[str] = None,
    count: float = 10,
    interval: str = "5m",
    convert: Optional[str] = None,
    convert_id: Optional[str] = None
) -> Any:
    """
    Returns an interval of historic quotes for any exchange based on time and interval parameters. **Technical Notes** - A historic quote for every "interval" period between your "time_start" and "time_end" will be returned. - If a "time_start" is not supplied, the "interval" will be applied in reverse from "time_end". - If "time_end" is not supplied, it defaults to the current time. - At each "interval" period, the historic quote that is closest in time to the requested time will be returned. - If no historic quotes are available in a given "interval" period up until the next interval period, it will be skipped. - This endpoint supports requesting multiple exchanges in the same call. Please note the API response will be wrapped in an additional object in this case. **Interval Options** There are 2 types of time interval formats that may be used for "interval". The first are calendar year and time constants in UTC time: **"hourly"** - Get the first quote available at the beginning of each calendar hour. **"daily"** - Get the first quote available at the beginning of each calendar day. **"weekly"** - Get the first quote available at the beginning of each calendar week. **"monthly"** - Get the first quote available at the beginning of each calendar month. **"yearly"** - Get the first quote available at the beginning of each calendar year. The second are relative time intervals. **"m"**: Get the first quote available every "m" minutes (60 second intervals). Supported minutes are: "5m", "10m", "15m", "30m", "45m". **"h"**: Get the first quote available every "h" hours (3600 second intervals). Supported hour intervals are: "1h", "2h", "3h", "4h", "6h", "12h". **"d"**: Get the first quote available every "d" days (86400 second intervals). Supported day intervals are: "1d", "2d", "3d", "7d", "14d", "15d", "30d", "60d", "90d", "365d". **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - ~~Basic~~ - Hobbyist (1 month) - Startup (1 month) - Standard (3 month) - Professional (Up to 12 months) - Enterprise (Up to 6 years) **Note:** You may use the /exchange/map endpoint to receive a list of earliest historical dates that may be fetched for each exchange as `first_historical_data`. This timestamp will either be the date CoinMarketCap first started tracking the exchange or 2018-04-26T00:45:00.000Z, the earliest date this type of historical data is available for. **Cache / Update frequency:** Every 5 minutes. **Plan credit use:** 1 call credit per 100 historical data points returned (rounded up) and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** No equivalent, this data is only available via API outside of our volume sparkline charts in [coinmarketcap.com/rankings/exchanges/](https://coinmarketcap.com/rankings/exchanges/).

    Generated from OpenAPI endpoint: GET /v1/exchange/quotes/historical

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        id: One or more comma-separated exchange CoinMarketCap ids. Example: "24,270" (optional) Examples: "24", "270"
        slug: Alternatively, one or more comma-separated exchange names in URL friendly shorthand "slug" format (all lowercase, spaces replaced with hyphens). Example: "binance,kraken". At least one "id" *or* "slug" is required. (optional) Examples: "binance", "kraken"
        time_start: Timestamp (Unix or ISO 8601) to start returning quotes for. Optional, if not passed, we'll return quotes calculated in reverse from "time_end". (optional)
        time_end: Timestamp (Unix or ISO 8601) to stop returning quotes for (inclusive). Optional, if not passed, we'll default to the current time. If no "time_start" is passed, we return quotes in reverse order starting from this time. (optional)
        count: The number of interval periods to return results for. Optional, required if both "time_start" and "time_end" aren't supplied. The default is 10 items. The current query limit is 10000. (optional, default: 10)
        interval: Interval of time to return data points for. See details in endpoint description. (optional, default: "5m")
        convert: By default market quotes are returned in USD. Optionally calculate market quotes in up to 3 other fiat currencies or cryptocurrencies. (optional)
        convert_id: Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await quotes_historical(slug="binance")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/exchange/quotes/historical"
        params = {
            "id": id,
            "slug": slug,
            "time_start": time_start,
            "time_end": time_end,
            "count": count,
            "interval": interval,
            "convert": convert,
            "convert_id": convert_id
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in quotes_historical: {e}")
        return {"error": str(e), "endpoint": "/v1/exchange/quotes/historical"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns a mapping of all supported fiat currencies"

)
async def coinmarketcap_id_map_1b83(
    context: Context,
    start: int = 1,
    limit: Optional[int] = None,
    sort: str = "id",
    include_metals: bool = False
) -> Any:
    """
    Returns a mapping of all supported fiat currencies to unique CoinMarketCap ids. Per our Best Practices we recommend utilizing CMC ID instead of currency symbols to securely identify assets with our other endpoints and in your own application logic. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Basic - Hobbyist - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** Mapping data is updated only as needed, every 30 seconds. **Plan credit use:** 1 API call credit per request no matter query size. **CMC equivalent pages:** No equivalent, this data is only available via API.

    Generated from OpenAPI endpoint: GET /v1/fiat/map

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        start: Optionally offset the start (1-based index) of the paginated list of items to return. (optional, default: 1)
        limit: Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size. (optional)
        sort: What field to sort the list by. (optional, default: "id")
        include_metals: Pass `true` to include precious metals. (optional, default: False)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await coinmarketcap_id_map_1b83()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/fiat/map"
        params = {
            "start": start,
            "limit": limit,
            "sort": sort,
            "include_metals": str(include_metals).lower()
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in coinmarketcap_id_map_1b83: {e}")
        return {"error": str(e), "endpoint": "/v1/fiat/map"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns an interval of historical global cryptocur"

)
async def quotes_historical_m0v0(
    context: Context,
    time_start: Optional[str] = None,
    time_end: Optional[str] = None,
    count: float = 10,
    interval: str = "1d",
    convert: Optional[str] = None,
    convert_id: Optional[str] = None,
    aux: str = "btc_dominance,eth_dominance,active_cryptocurrencies,active_exchanges,active_market_pairs,total_volume_24h,total_volume_24h_reported,altcoin_market_cap,altcoin_volume_24h,altcoin_volume_24h_reported"
) -> Any:
    """
    Returns an interval of historical global cryptocurrency market metrics based on time and interval parameters. **Technical Notes** - A historic quote for every "interval" period between your "time_start" and "time_end" will be returned. - If a "time_start" is not supplied, the "interval" will be applied in reverse from "time_end". - If "time_end" is not supplied, it defaults to the current time. - At each "interval" period, the historic quote that is closest in time to the requested time will be returned. - If no historic quotes are available in a given "interval" period up until the next interval period, it will be skipped. **Interval Options** There are 2 types of time interval formats that may be used for "interval". The first are calendar year and time constants in UTC time: **"hourly"** - Get the first quote available at the beginning of each calendar hour. **"daily"** - Get the first quote available at the beginning of each calendar day. **"weekly"** - Get the first quote available at the beginning of each calendar week. **"monthly"** - Get the first quote available at the beginning of each calendar month. **"yearly"** - Get the first quote available at the beginning of each calendar year. The second are relative time intervals. **"m"**: Get the first quote available every "m" minutes (60 second intervals). Supported minutes are: "5m", "10m", "15m", "30m", "45m". **"h"**: Get the first quote available every "h" hours (3600 second intervals). Supported hour intervals are: "1h", "2h", "3h", "4h", "6h", "12h". **"d"**: Get the first quote available every "d" days (86400 second intervals). Supported day intervals are: "1d", "2d", "3d", "7d", "14d", "15d", "30d", "60d", "90d", "365d". **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - ~~Basic~~ - Hobbyist (1 month) - Startup (1 month) - Standard (3 month) - Professional (12 months) - Enterprise (Up to 6 years) **Cache / Update frequency:** Every 5 minutes. **Plan credit use:** 1 call credit per 100 historical data points returned (rounded up). **CMC equivalent pages:** Our Total Market Capitalization global chart [coinmarketcap.com/charts/](https://coinmarketcap.com/charts/).

    Generated from OpenAPI endpoint: GET /v1/global-metrics/quotes/historical

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        time_start: Timestamp (Unix or ISO 8601) to start returning quotes for. Optional, if not passed, we'll return quotes calculated in reverse from "time_end". (optional)
        time_end: Timestamp (Unix or ISO 8601) to stop returning quotes for (inclusive). Optional, if not passed, we'll default to the current time. If no "time_start" is passed, we return quotes in reverse order starting from this time. (optional)
        count: The number of interval periods to return results for. Optional, required if both "time_start" and "time_end" aren't supplied. The default is 10 items. The current query limit is 10000. (optional, default: 10)
        interval: Interval of time to return data points for. See details in endpoint description. (optional, default: "1d")
        convert: By default market quotes are returned in USD. Optionally calculate market quotes in up to 3 other fiat currencies or cryptocurrencies. (optional)
        convert_id: Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)
        aux: Optionally specify a comma-separated list of supplemental data fields to return. Pass `btc_dominance,eth_dominance,active_cryptocurrencies,active_exchanges,active_market_pairs,total_volume_24h,total_volume_24h_reported,altcoin_market_cap,altcoin_volume_24h,altcoin_volume_24h_reported,search_interval` to include all auxiliary fields. (optional, default: "btc_dominance,eth_dominance,active_cryptocurrencies,active_exchanges,active_market_pairs,total_volume_24h,total_volume_24h_reported,altcoin_market_cap,altcoin_volume_24h,altcoin_volume_24h_reported")

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await quotes_historical_m0v0()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/historical"
        params = {
            "time_start": time_start,
            "time_end": time_end,
            "count": count,
            "interval": interval,
            "convert": convert,
            "convert_id": convert_id,
            "aux": aux
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in quotes_historical_m0v0: {e}")
        return {"error": str(e), "endpoint": "/v1/global-metrics/quotes/historical"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns the latest global cryptocurrency market me"

)
async def quotes_latest_qen5(
    context: Context,
    convert: Optional[str] = None,
    convert_id: Optional[str] = None
) -> Any:
    """
    Returns the latest global cryptocurrency market metrics. Use the "convert" option to return market values in multiple fiat and cryptocurrency conversions in the same call. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Basic - Hobbyist - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** Every 5 minute. **Plan credit use:** 1 call credit per call and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** The latest aggregate global market stats ticker across all CMC pages like [coinmarketcap.com](https://coinmarketcap.com/).

    Generated from OpenAPI endpoint: GET /v1/global-metrics/quotes/latest

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        convert: Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found [here](#section/Standards-and-Conventions). Each conversion is returned in its own "quote" object. (optional)
        convert_id: Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await quotes_latest_qen5()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest"
        params = {
            "convert": convert,
            "convert_id": convert_id
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in quotes_latest_qen5: {e}")
        return {"error": str(e), "endpoint": "/v1/global-metrics/quotes/latest"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns API key details and usage stats. This endp"

)
async def key_info(
    context: Context
) -> Any:
    """
    Returns API key details and usage stats. This endpoint can be used to programmatically monitor your key usage compared to the rate limit and daily/monthly credit limits available to your API plan. You may use the Developer Portal's account dashboard as an alternative to this endpoint. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Basic - Hobbyist - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** No cache, this endpoint updates as requests are made with your key. **Plan credit use:** No API credit cost. Requests to this endpoint do contribute to your minute based rate limit however. **CMC equivalent pages:** Our Developer Portal dashboard for your API Key at [pro.coinmarketcap.com/account](https://pro.coinmarketcap.com/account).

    Generated from OpenAPI endpoint: GET /v1/key/info

    Args:
        context: MCP context (auto-injected by framework, not user-provided)


    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await key_info()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/key/info"
        params = {}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in key_info: {e}")
        return {"error": str(e), "endpoint": "/v1/key/info"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Convert APIs into postman format. You can referenc"

)
async def postman_conversion_v1(
    context: Context
) -> Any:
    """
    Convert APIs into postman format. You can reference the operation from <a href="https://coinmarketcap.com/alexandria/article/register-for-coinmarketcap-api" target="_blank"><b>this article</b></a>. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Free - Hobbyist - Startup - Standard - Professional - Enterprise **Technical Notes** - Set the env variables in the postman: {{baseUrl}}, {{API_KEY}}

    Generated from OpenAPI endpoint: GET /v1/tools/postman

    Args:
        context: MCP context (auto-injected by framework, not user-provided)


    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await postman_conversion_v1()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v1/tools/postman"
        params = {}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in postman_conversion_v1: {e}")
        return {"error": str(e), "endpoint": "/v1/tools/postman"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns all static metadata available for one or m"

)
async def metadata_v2(
    context: Context,
    symbol: str,
    id: Optional[str] = None,
    slug: Optional[str] = None,
    address: Optional[str] = None,
    skip_invalid: bool = False,
    aux: str = "urls,logo,description,tags,platform,date_added,notice"
) -> Any:
    """
    Returns all static metadata available for one or more cryptocurrencies. This information includes details like logo, description, official website URL, social links, and links to a cryptocurrency's technical documentation. **Please note**: This documentation relates to our updated V2 endpoint, which may be incompatible with our V1 versions. Documentation for deprecated endpoints can be found <a href="#tag/deprecated">here</a>.<br><br> **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Basic - Startup - Hobbyist - Standard - Professional - Enterprise **Cache / Update frequency:** Static data is updated only as needed, every 30 seconds. **Plan credit use:** 1 call credit per 100 cryptocurrencies returned (rounded up). **CMC equivalent pages:** Cryptocurrency detail page metadata like [coinmarketcap.com/currencies/bitcoin/](https://coinmarketcap.com/currencies/bitcoin/).

    Generated from OpenAPI endpoint: GET /v2/cryptocurrency/info

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        id: One or more comma-separated CoinMarketCap cryptocurrency IDs. Example: "1,2" (optional) Examples: "1", "2"
        slug: Alternatively pass a comma-separated list of cryptocurrency slugs. Example: "bitcoin,ethereum" (optional) Examples: "bitcoin", "ethereum"
        symbol: Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". At least one "id" *or* "slug" *or* "symbol" is required for this request. Please note that starting in the v2 endpoint, due to the fact that a symbol is not unique, if you request by symbol each data response will contain an array of objects containing all of the coins that use each requested symbol. The v1 endpoint will still return a single object, the highest ranked coin using that symbol. (optional) Examples: "BTC", "ETH"
        address: Alternatively pass in a contract address. Example: "0xc40af1e4fecfa05ce6bab79dcd8b373d2e436c4e" (optional) Examples: "0xc40af1e4fecfa05ce6bab79dcd8b373d2e436c4e"
        skip_invalid: Pass `true` to relax request validation rules. When requesting records on multiple cryptocurrencies an error is returned if any invalid cryptocurrencies are requested or a cryptocurrency does not have matching records in the requested timeframe. If set to true, invalid lookups will be skipped allowing valid cryptocurrencies to still be returned. (optional, default: False)
        aux: Optionally specify a comma-separated list of supplemental data fields to return. Pass `urls,logo,description,tags,platform,date_added,notice,status` to include all auxiliary fields. (optional, default: "urls,logo,description,tags,platform,date_added,notice")

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await metadata_v2(symbol="BTC")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/info"
        params = {
            "id": id,
            "slug": slug,
            "symbol": symbol,
            "address": address,
            "skip_invalid": str(skip_invalid).lower(),
            "aux": aux
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in metadata_v2: {e}")
        return {"error": str(e), "endpoint": "/v2/cryptocurrency/info"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns historical OHLCV (Open, High, Low, Close, "

)
async def ohlcv_historical_v2(
    context: Context,
    symbol: str,
    id: Optional[str] = None,
    slug: Optional[str] = None,
    time_period: str = "daily",
    time_start: Optional[str] = None,
    time_end: Optional[str] = None,
    count: float = 10,
    interval: str = "daily",
    convert: Optional[str] = None,
    convert_id: Optional[str] = None,
    skip_invalid: bool = True
) -> Any:
    """
    Returns historical OHLCV (Open, High, Low, Close, Volume) data along with market cap for any cryptocurrency using time interval parameters. Currently daily and hourly OHLCV periods are supported. Volume is not currently supported for hourly OHLCV intervals before 2020-09-22. **Please note**: This documentation relates to our updated V2 endpoint, which may be incompatible with our V1 versions. Documentation for deprecated endpoints can be found <a href="#tag/deprecated">here</a>.<br><br> **Technical Notes** - Only the date portion of the timestamp is used for daily OHLCV so it's recommended to send an ISO date format like "2018-09-19" without time for this "time_period". - One OHLCV quote will be returned for every "time_period" between your "time_start" (exclusive) and "time_end" (inclusive). - If a "time_start" is not supplied, the "time_period" will be calculated in reverse from "time_end" using the "count" parameter which defaults to 10 results. - If "time_end" is not supplied, it defaults to the current time. - If you don't need every "time_period" between your dates you may adjust the frequency that "time_period" is sampled using the "interval" parameter. For example with "time_period" set to "daily" you may set "interval" to "2d" to get the daily OHLCV for every other day. You could set "interval" to "monthly" to get the first daily OHLCV for each month, or set it to "yearly" to get the daily OHLCV value against the same date every year. **Implementation Tips** - If querying for a specific OHLCV date your "time_start" should specify a timestamp of 1 interval prior as "time_start" is an exclusive time parameter (as opposed to "time_end" which is inclusive to the search). This means that when you pass a "time_start" results will be returned for the *next* complete "time_period". For example, if you are querying for a daily OHLCV datapoint for 2018-11-30 your "time_start" should be "2018-11-29". - If only specifying a "count" parameter to return latest OHLCV periods, your "count" should be 1 number higher than the number of results you expect to receive. "Count" defines the number of "time_period" intervals queried, *not* the number of results to return, and this includes the currently active time period which is incomplete when working backwards from current time. For example, if you want the last daily OHLCV value available simply pass "count=2" to skip the incomplete active time period. - This endpoint supports requesting multiple cryptocurrencies in the same call. Please note the API response will be wrapped in an additional object in this case. **Interval Options** There are 2 types of time interval formats that may be used for "time_period" and "interval" parameters. For "time_period" these return aggregate OHLCV data from the beginning to end of each interval period. Apply these time intervals to "interval" to adjust how frequently "time_period" is sampled. The first are calendar year and time constants in UTC time: **"hourly"** - Hour intervals in UTC. **"daily"** - Calendar day intervals for each UTC day. **"weekly"** - Calendar week intervals for each calendar week. **"monthly"** - Calendar month intervals for each calendar month. **"yearly"** - Calendar year intervals for each calendar year. The second are relative time intervals. **"h"**: Get the first quote available every "h" hours (3600 second intervals). Supported hour intervals are: "1h", "2h", "3h", "4h", "6h", "12h". **"d"**: Time periods that repeat every "d" days (86400 second intervals). Supported day intervals are: "1d", "2d", "3d", "7d", "14d", "15d", "30d", "60d", "90d", "365d". Please note that "time_period" currently supports the "daily" and "hourly" options. "interval" supports all interval options. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - ~~Basic~~ - ~~Hobbyist~~ - Startup (1 month) - Standard (3 months) - Professional (12 months) - Enterprise (Up to 6 years) **Cache / Update frequency:** Latest Daily OHLCV record is available ~5 to ~10 minutes after each midnight UTC. The latest hourly OHLCV record is available 5 minutes after each UTC hour. **Plan credit use:** 1 call credit per 100 OHLCV data points returned (rounded up) and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** Our historical cryptocurrency data pages like [coinmarketcap.com/currencies/bitcoin/historical-data/](https://coinmarketcap.com/currencies/bitcoin/historical-data/).

    Generated from OpenAPI endpoint: GET /v2/cryptocurrency/ohlcv/historical

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        id: One or more comma-separated CoinMarketCap cryptocurrency IDs. Example: "1,1027" (optional) Examples: "1", "1027"
        slug: Alternatively pass a comma-separated list of cryptocurrency slugs. Example: "bitcoin,ethereum" (optional) Examples: "bitcoin", "ethereum"
        symbol: Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". At least one "id" *or* "slug" *or* "symbol" is required for this request. (optional) Examples: "BTC", "ETH"
        time_period: Time period to return OHLCV data for. The default is "daily". If hourly, the open will be 01:00 and the close will be 01:59. If daily, the open will be 00:00:00 for the day and close will be 23:59:99 for the same day. See the main endpoint description for details. (optional, default: "daily")
        time_start: Timestamp (Unix or ISO 8601) to start returning OHLCV time periods for. Only the date portion of the timestamp is used for daily OHLCV so it's recommended to send an ISO date format like "2018-09-19" without time. (optional)
        time_end: Timestamp (Unix or ISO 8601) to stop returning OHLCV time periods for (inclusive). Optional, if not passed we'll default to the current time. Only the date portion of the timestamp is used for daily OHLCV so it's recommended to send an ISO date format like "2018-09-19" without time. (optional)
        count: Optionally limit the number of time periods to return results for. The default is 10 items. The current query limit is 10000 items. (optional, default: 10)
        interval: Optionally adjust the interval that "time_period" is sampled. For example with interval=monthly&time_period=daily you will see a daily OHLCV record for January, February, March and so on. See main endpoint description for available options. (optional, default: "daily")
        convert: By default market quotes are returned in USD. Optionally calculate market quotes in up to 3 fiat currencies or cryptocurrencies. (optional)
        convert_id: Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)
        skip_invalid: Pass `true` to relax request validation rules. When requesting records on multiple cryptocurrencies an error is returned if any invalid cryptocurrencies are requested or a cryptocurrency does not have matching records in the requested timeframe. If set to true, invalid lookups will be skipped allowing valid cryptocurrencies to still be returned. (optional, default: True)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await ohlcv_historical_v2(symbol="BTC")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/ohlcv/historical"
        params = {
            "id": id,
            "slug": slug,
            "symbol": symbol,
            "time_period": time_period,
            "time_start": time_start,
            "time_end": time_end,
            "count": count,
            "interval": interval,
            "convert": convert,
            "convert_id": convert_id,
            "skip_invalid": str(skip_invalid).lower()
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in ohlcv_historical_v2: {e}")
        return {"error": str(e), "endpoint": "/v2/cryptocurrency/ohlcv/historical"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns the latest OHLCV (Open, High, Low, Close, "

)
async def ohlcv_latest_v2(
    context: Context,
    symbol: str,
    id: Optional[str] = None,
    convert: Optional[str] = None,
    convert_id: Optional[str] = None,
    skip_invalid: bool = True
) -> Any:
    """
    Returns the latest OHLCV (Open, High, Low, Close, Volume) market values for one or more cryptocurrencies for the current UTC day. Since the current UTC day is still active these values are updated frequently. You can find the final calculated OHLCV values for the last completed UTC day along with all historic days using /cryptocurrency/ohlcv/historical. **Please note**: This documentation relates to our updated V2 endpoint, which may be incompatible with our V1 versions. Documentation for deprecated endpoints can be found <a href="#tag/deprecated">here</a>.<br><br> **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - ~~Basic~~ - ~~Hobbyist~~ - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** Every 10 minutes. Additional OHLCV intervals and 1 minute updates will be available in the future. **Plan credit use:** 1 call credit per 100 OHLCV values returned (rounded up) and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** No equivalent, this data is only available via API.

    Generated from OpenAPI endpoint: GET /v2/cryptocurrency/ohlcv/latest

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        id: One or more comma-separated cryptocurrency CoinMarketCap IDs. Example: 1,2 (optional) Examples: "1", "2"
        symbol: Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". At least one "id" *or* "symbol" is required. (optional) Examples: "BTC", "ETH"
        convert: Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found [here](#section/Standards-and-Conventions). Each conversion is returned in its own "quote" object. (optional)
        convert_id: Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)
        skip_invalid: Pass `true` to relax request validation rules. When requesting records on multiple cryptocurrencies an error is returned if any invalid cryptocurrencies are requested or a cryptocurrency does not have matching records in the requested timeframe. If set to true, invalid lookups will be skipped allowing valid cryptocurrencies to still be returned. (optional, default: True)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await ohlcv_latest_v2(symbol="BTC")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/ohlcv/latest"
        params = {
            "id": id,
            "symbol": symbol,
            "convert": convert,
            "convert_id": convert_id,
            "skip_invalid": str(skip_invalid).lower()
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in ohlcv_latest_v2: {e}")
        return {"error": str(e), "endpoint": "/v2/cryptocurrency/ohlcv/latest"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns price performance statistics for one or mo"

)
async def price_performance_stats_v2(
    context: Context,
    symbol: str,
    id: Optional[str] = None,
    slug: Optional[str] = None,
    time_period: str = "all_time",
    convert: Optional[str] = None,
    convert_id: Optional[str] = None,
    skip_invalid: bool = True
) -> Any:
    """
    Returns price performance statistics for one or more cryptocurrencies including launch price ROI and all-time high / all-time low. Stats are returned for an `all_time` period by default. UTC `yesterday` and a number of *rolling time periods* may be requested using the `time_period` parameter. Utilize the `convert` parameter to translate values into multiple fiats or cryptocurrencies using historical rates. **Please note**: This documentation relates to our updated V2 endpoint, which may be incompatible with our V1 versions. Documentation for deprecated endpoints can be found <a href="#tag/deprecated">here</a>.<br><br> **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - ~~Basic~~ - ~~Hobbyist~~ - Startup - Standard - Professional - Enterprise **Cache / Update frequency:** Every 60 seconds. **Plan credit use:** 1 call credit per 100 cryptocurrencies returned (rounded up) and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** The statistics module displayed on cryptocurrency pages like [Bitcoin](https://coinmarketcap.com/currencies/bitcoin/). ***NOTE:** You may also use [/cryptocurrency/ohlcv/historical](#operation/getV1CryptocurrencyOhlcvHistorical) for traditional OHLCV data at historical daily and hourly intervals. You may also use [/v1/cryptocurrency/ohlcv/latest](#operation/getV1CryptocurrencyOhlcvLatest) for OHLCV data for the current UTC day.*

    Generated from OpenAPI endpoint: GET /v2/cryptocurrency/price-performance-stats/latest

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        id: One or more comma-separated cryptocurrency CoinMarketCap IDs. Example: 1,2 (optional) Examples: "1", "2"
        slug: Alternatively pass a comma-separated list of cryptocurrency slugs. Example: "bitcoin,ethereum" (optional) Examples: "bitcoin", "ethereum"
        symbol: Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". At least one "id" *or* "slug" *or* "symbol" is required for this request. (optional) Examples: "BTC", "ETH"
        time_period: Specify one or more comma-delimited time periods to return stats for. `all_time` is the default. Pass `all_time,yesterday,24h,7d,30d,90d,365d` to return all supported time periods. All rolling periods have a rolling close time of the current request time. For example `24h` would have a close time of now and an open time of 24 hours before now. *Please note: `yesterday` is a UTC period and currently does not currently support `high` and `low` timestamps.* (optional, default: "all_time")
        convert: Optionally calculate quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found [here](#section/Standards-and-Conventions). Each conversion is returned in its own "quote" object. (optional)
        convert_id: Optionally calculate quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)
        skip_invalid: Pass `true` to relax request validation rules. When requesting records on multiple cryptocurrencies an error is returned if no match is found for 1 or more requested cryptocurrencies. If set to true, invalid lookups will be skipped allowing valid cryptocurrencies to still be returned. (optional, default: True)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await price_performance_stats_v2(symbol="BTC")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/price-performance-stats/latest"
        params = {
            "id": id,
            "slug": slug,
            "symbol": symbol,
            "time_period": time_period,
            "convert": convert,
            "convert_id": convert_id,
            "skip_invalid": str(skip_invalid).lower()
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in price_performance_stats_v2: {e}")
        return {"error": str(e), "endpoint": "/v2/cryptocurrency/price-performance-stats/latest"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns an interval of historic market quotes for "

)
async def quotes_historical_v2(
    context: Context,
    symbol: str,
    id: Optional[str] = None,
    time_start: Optional[str] = None,
    time_end: Optional[str] = None,
    count: float = 10,
    interval: str = "5m",
    convert: Optional[str] = None,
    convert_id: Optional[str] = None,
    aux: str = "price,volume,market_cap,circulating_supply,total_supply,quote_timestamp,is_active,is_fiat",
    skip_invalid: bool = True
) -> Any:
    """
    Returns an interval of historic market quotes for any cryptocurrency based on time and interval parameters. **Please note**: This documentation relates to our updated V2 endpoint, which may be incompatible with our V1 versions. Documentation for deprecated endpoints can be found <a href="#tag/deprecated">here</a>.<br><br> **Technical Notes** - A historic quote for every "interval" period between your "time_start" and "time_end" will be returned. - If a "time_start" is not supplied, the "interval" will be applied in reverse from "time_end". - If "time_end" is not supplied, it defaults to the current time. - At each "interval" period, the historic quote that is closest in time to the requested time will be returned. - If no historic quotes are available in a given "interval" period up until the next interval period, it will be skipped. **Implementation Tips** - Want to get the last quote of each UTC day? Don't use "interval=daily" as that returns the first quote. Instead use "interval=24h" to repeat a specific timestamp search every 24 hours and pass ex. "time_start=2019-01-04T23:59:00.000Z" to query for the last record of each UTC day. - This endpoint supports requesting multiple cryptocurrencies in the same call. Please note the API response will be wrapped in an additional object in this case. **Interval Options** There are 2 types of time interval formats that may be used for "interval". The first are calendar year and time constants in UTC time: **"hourly"** - Get the first quote available at the beginning of each calendar hour. **"daily"** - Get the first quote available at the beginning of each calendar day. **"weekly"** - Get the first quote available at the beginning of each calendar week. **"monthly"** - Get the first quote available at the beginning of each calendar month. **"yearly"** - Get the first quote available at the beginning of each calendar year. The second are relative time intervals. **"m"**: Get the first quote available every "m" minutes (60 second intervals). Supported minutes are: "5m", "10m", "15m", "30m", "45m". **"h"**: Get the first quote available every "h" hours (3600 second intervals). Supported hour intervals are: "1h", "2h", "3h", "4h", "6h", "12h". **"d"**: Get the first quote available every "d" days (86400 second intervals). Supported day intervals are: "1d", "2d", "3d", "7d", "14d", "15d", "30d", "60d", "90d", "365d". **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - ~~Basic~~ - Hobbyist (1 month) - Startup (1 month) - Standard (3 month) - Professional (12 months) - Enterprise (Up to 6 years) **Cache / Update frequency:** Every 5 minutes. **Plan credit use:** 1 call credit per 100 historical data points returned (rounded up) and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** Our historical cryptocurrency charts like [coinmarketcap.com/currencies/bitcoin/#charts](https://coinmarketcap.com/currencies/bitcoin/#charts).

    Generated from OpenAPI endpoint: GET /v2/cryptocurrency/quotes/historical

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        id: One or more comma-separated CoinMarketCap cryptocurrency IDs. Example: "1,2" (optional) Examples: "1", "2"
        symbol: Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". At least one "id" *or* "symbol" is required for this request. (optional) Examples: "BTC", "ETH"
        time_start: Timestamp (Unix or ISO 8601) to start returning quotes for. Optional, if not passed, we'll return quotes calculated in reverse from "time_end". (optional)
        time_end: Timestamp (Unix or ISO 8601) to stop returning quotes for (inclusive). Optional, if not passed, we'll default to the current time. If no "time_start" is passed, we return quotes in reverse order starting from this time. (optional)
        count: The number of interval periods to return results for. Optional, required if both "time_start" and "time_end" aren't supplied. The default is 10 items. The current query limit is 10000. (optional, default: 10)
        interval: Interval of time to return data points for. See details in endpoint description. (optional, default: "5m")
        convert: By default market quotes are returned in USD. Optionally calculate market quotes in up to 3 other fiat currencies or cryptocurrencies. (optional)
        convert_id: Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)
        aux: Optionally specify a comma-separated list of supplemental data fields to return. Pass `price,volume,market_cap,circulating_supply,total_supply,quote_timestamp,is_active,is_fiat,search_interval` to include all auxiliary fields. (optional, default: "price,volume,market_cap,circulating_supply,total_supply,quote_timestamp,is_active,is_fiat")
        skip_invalid: Pass `true` to relax request validation rules. When requesting records on multiple cryptocurrencies an error is returned if no match is found for 1 or more requested cryptocurrencies. If set to true, invalid lookups will be skipped allowing valid cryptocurrencies to still be returned. (optional, default: True)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await quotes_historical_v2(symbol="BTC")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/historical"
        params = {
            "id": id,
            "symbol": symbol,
            "time_start": time_start,
            "time_end": time_end,
            "count": count,
            "interval": interval,
            "convert": convert,
            "convert_id": convert_id,
            "aux": aux,
            "skip_invalid": str(skip_invalid).lower()
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in quotes_historical_v2: {e}")
        return {"error": str(e), "endpoint": "/v2/cryptocurrency/quotes/historical"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns the latest market quote for 1 or more cryp"

)
async def quotes_latest_v2(
    context: Context,
    symbol: str,
    id: Optional[str] = None,
    slug: Optional[str] = None,
    convert: Optional[str] = None,
    convert_id: Optional[str] = None,
    aux: str = "num_market_pairs,cmc_rank,date_added,tags,platform,max_supply,circulating_supply,total_supply,is_active,is_fiat",
    skip_invalid: bool = True
) -> Any:
    """
    Returns the latest market quote for 1 or more cryptocurrencies. Use the "convert" option to return market values in multiple fiat and cryptocurrency conversions in the same call. **Please note**: This documentation relates to our updated V2 endpoint, which may be incompatible with our V1 versions. Documentation for deprecated endpoints can be found <a href="#tag/deprecated">here</a>.<br><br> **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Basic - Startup - Hobbyist - Standard - Professional - Enterprise **Cache / Update frequency:** Every 60 seconds. **Plan credit use:** 1 call credit per 100 cryptocurrencies returned (rounded up) and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** Latest market data pages for specific cryptocurrencies like [coinmarketcap.com/currencies/bitcoin/](https://coinmarketcap.com/currencies/bitcoin/). ***NOTE:** Use this endpoint to request the latest quote for specific cryptocurrencies. If you need to request all cryptocurrencies use [/v1/cryptocurrency/listings/latest](#operation/getV1CryptocurrencyListingsLatest) which is optimized for that purpose. The response data between these endpoints is otherwise the same.*

    Generated from OpenAPI endpoint: GET /v2/cryptocurrency/quotes/latest

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        id: One or more comma-separated cryptocurrency CoinMarketCap IDs. Example: 1,2 (optional) Examples: "1", "2"
        slug: Alternatively pass a comma-separated list of cryptocurrency slugs. Example: "bitcoin,ethereum" (optional) Examples: "bitcoin", "ethereum"
        symbol: Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". At least one "id" *or* "slug" *or* "symbol" is required for this request. (optional) Examples: "BTC", "ETH"
        convert: Optionally calculate market quotes in up to 120 currencies at once by passing a comma-separated list of cryptocurrency or fiat currency symbols. Each additional convert option beyond the first requires an additional call credit. A list of supported fiat options can be found [here](#section/Standards-and-Conventions). Each conversion is returned in its own "quote" object. (optional)
        convert_id: Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)
        aux: Optionally specify a comma-separated list of supplemental data fields to return. Pass `num_market_pairs,cmc_rank,date_added,tags,platform,max_supply,circulating_supply,total_supply,market_cap_by_total_supply,volume_24h_reported,volume_7d,volume_7d_reported,volume_30d,volume_30d_reported,is_active,is_fiat` to include all auxiliary fields. (optional, default: "num_market_pairs,cmc_rank,date_added,tags,platform,max_supply,circulating_supply,total_supply,is_active,is_fiat")
        skip_invalid: Pass `true` to relax request validation rules. When requesting records on multiple cryptocurrencies an error is returned if no match is found for 1 or more requested cryptocurrencies. If set to true, invalid lookups will be skipped allowing valid cryptocurrencies to still be returned. (optional, default: True)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await quotes_latest_v2(symbol="BTC")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v2/cryptocurrency/quotes/latest"
        params = {
            "id": id,
            "slug": slug,
            "symbol": symbol,
            "convert": convert,
            "convert_id": convert_id,
            "aux": aux,
            "skip_invalid": str(skip_invalid).lower()
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in quotes_latest_v2: {e}")
        return {"error": str(e), "endpoint": "/v2/cryptocurrency/quotes/latest"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Convert an amount of one cryptocurrency or fiat cu"

)
async def price_conversion_v2(
    context: Context,
    amount: float,
    symbol: str,
    id: Optional[str] = None,
    time: Optional[str] = None,
    convert: Optional[str] = None,
    convert_id: Optional[str] = None
) -> Any:
    """
    Convert an amount of one cryptocurrency or fiat currency into one or more different currencies utilizing the latest market rate for each currency. You may optionally pass a historical timestamp as `time` to convert values based on historical rates (as your API plan supports). **Please note**: This documentation relates to our updated V2 endpoint, which may be incompatible with our V1 versions. Documentation for deprecated endpoints can be found <a href="#tag/deprecated">here</a>.<br><br> **Technical Notes** - Latest market rate conversions are accurate to 1 minute of specificity. Historical conversions are accurate to 1 minute of specificity outside of non-USD fiat conversions which have 5 minute specificity. - You may reference a current list of all supported cryptocurrencies via the <a href="/api/v1/#section/Standards-and-Conventions" target="_blank">cryptocurrency/map</a> endpoint. This endpoint also returns the supported date ranges for historical conversions via the `first_historical_data` and `last_historical_data` properties. - Conversions are supported in 93 different fiat currencies and 4 precious metals <a href="/api/v1/#section/Standards-and-Conventions" target="_blank">as outlined here</a>. Historical fiat conversions are supported as far back as 2013-04-28. - A `last_updated` timestamp is included for both your source currency and each conversion currency. This is the timestamp of the closest market rate record referenced for each currency during the conversion. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Basic (Latest market price conversions) - Hobbyist (Latest market price conversions + 1 month historical) - Startup (Latest market price conversions + 1 month historical) - Standard (Latest market price conversions + 3 months historical) - Professional (Latest market price conversions + 12 months historical) - Enterprise (Latest market price conversions + up to 6 years historical) **Cache / Update frequency:** Every 60 seconds for the lastest cryptocurrency and fiat currency rates. **Plan credit use:** 1 call credit per call and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** Our cryptocurrency conversion page at [coinmarketcap.com/converter/](https://coinmarketcap.com/converter/).

    Generated from OpenAPI endpoint: GET /v2/tools/price-conversion

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        amount: An amount of currency to convert. Example: 10.43 (optional) Examples: 10
        id: The CoinMarketCap currency ID of the base cryptocurrency or fiat to convert from. Example: "1" (optional) Examples: "1"
        symbol: Alternatively the currency symbol of the base cryptocurrency or fiat to convert from. Example: "BTC". One "id" *or* "symbol" is required. Please note that starting in the v2 endpoint, due to the fact that a symbol is not unique, if you request by symbol each quote response will contain an array of objects containing all of the coins that use each requested symbol. The v1 endpoint will still return a single object, the highest ranked coin using that symbol. (optional) Examples: "BTC"
        time: Optional timestamp (Unix or ISO 8601) to reference historical pricing during conversion. If not passed, the current time will be used. If passed, we'll reference the closest historic values available for this conversion. (optional)
        convert: Pass up to 120 comma-separated fiat or cryptocurrency symbols to convert the source amount to. (optional)
        convert_id: Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await price_conversion_v2(amount=10, symbol="BTC")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v2/tools/price-conversion"
        params = {
            "amount": amount,
            "id": id,
            "symbol": symbol,
            "time": time,
            "convert": convert,
            "convert_id": convert_id
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in price_conversion_v2: {e}")
        return {"error": str(e), "endpoint": "/v2/tools/price-conversion"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns an interval of historic market quotes for "

)
async def quotes_historical_v3(
    context: Context,
    symbol: str,
    id: Optional[str] = None,
    time_start: Optional[str] = None,
    time_end: Optional[str] = None,
    count: float = 10,
    interval: str = "5m",
    convert: Optional[str] = None,
    convert_id: Optional[str] = None,
    aux: str = "price,volume,market_cap,circulating_supply,total_supply,quote_timestamp,is_active,is_fiat",
    skip_invalid: bool = True
) -> Any:
    """
    Returns an interval of historic market quotes for any cryptocurrency based on time and interval parameters. **Please note**: This documentation relates to our updated V3 endpoint, which may be incompatible with our V1 versions. Documentation for deprecated endpoints can be found <a href="#tag/deprecated">here</a>.<br><br> **Technical Notes** - A historic quote for every "interval" period between your "time_start" and "time_end" will be returned. - If a "time_start" is not supplied, the "interval" will be applied in reverse from "time_end". - If "time_end" is not supplied, it defaults to the current time. - At each "interval" period, the historic quote that is closest in time to the requested time will be returned. - If no historic quotes are available in a given "interval" period up until the next interval period, it will be skipped. **Implementation Tips** - Want to get the last quote of each UTC day? Don't use "interval=daily" as that returns the first quote. Instead use "interval=24h" to repeat a specific timestamp search every 24 hours and pass ex. "time_start=2019-01-04T23:59:00.000Z" to query for the last record of each UTC day. - This endpoint supports requesting multiple cryptocurrencies in the same call. Please note the API response will be wrapped in an additional object in this case. **Interval Options** There are 2 types of time interval formats that may be used for "interval". The first are calendar year and time constants in UTC time: **"hourly"** - Get the first quote available at the beginning of each calendar hour. **"daily"** - Get the first quote available at the beginning of each calendar day. **"weekly"** - Get the first quote available at the beginning of each calendar week. **"monthly"** - Get the first quote available at the beginning of each calendar month. **"yearly"** - Get the first quote available at the beginning of each calendar year. The second are relative time intervals. **"m"**: Get the first quote available every "m" minutes (60 second intervals). Supported minutes are: "5m", "10m", "15m", "30m", "45m". **"h"**: Get the first quote available every "h" hours (3600 second intervals). Supported hour intervals are: "1h", "2h", "3h", "4h", "6h", "12h". **"d"**: Get the first quote available every "d" days (86400 second intervals). Supported day intervals are: "1d", "2d", "3d", "7d", "14d", "15d", "30d", "60d", "90d", "365d". **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - ~~Basic~~ - Hobbyist (1 month) - Startup (1 month) - Standard (3 month) - Professional (12 months) - Enterprise (Up to 6 years) **Cache / Update frequency:** Every 5 minutes. **Plan credit use:** 1 call credit per 100 historical data points returned (rounded up) and 1 call credit per `convert` option beyond the first. **CMC equivalent pages:** Our historical cryptocurrency charts like [coinmarketcap.com/currencies/bitcoin/#charts](https://coinmarketcap.com/currencies/bitcoin/#charts).

    Generated from OpenAPI endpoint: GET /v3/cryptocurrency/quotes/historical

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        id: One or more comma-separated CoinMarketCap cryptocurrency IDs. Example: "1,2" (optional) Examples: "1", "2"
        symbol: Alternatively pass one or more comma-separated cryptocurrency symbols. Example: "BTC,ETH". At least one "id" *or* "symbol" is required for this request. (optional) Examples: "BTC", "ETH"
        time_start: Timestamp (Unix or ISO 8601) to start returning quotes for. Optional, if not passed, we'll return quotes calculated in reverse from "time_end". (optional)
        time_end: Timestamp (Unix or ISO 8601) to stop returning quotes for (inclusive). Optional, if not passed, we'll default to the current time. If no "time_start" is passed, we return quotes in reverse order starting from this time. (optional)
        count: The number of interval periods to return results for. Optional, required if both "time_start" and "time_end" aren't supplied. The default is 10 items. The current query limit is 10000. (optional, default: 10)
        interval: Interval of time to return data points for. See details in endpoint description. (optional, default: "5m")
        convert: By default market quotes are returned in USD. Optionally calculate market quotes in up to 3 other fiat currencies or cryptocurrencies. (optional)
        convert_id: Optionally calculate market quotes by CoinMarketCap ID instead of symbol. This option is identical to `convert` outside of ID format. Ex: convert_id=1,2781 would replace convert=BTC,USD in your query. This parameter cannot be used when `convert` is used. (optional)
        aux: Optionally specify a comma-separated list of supplemental data fields to return. Pass `price,volume,market_cap,circulating_supply,total_supply,quote_timestamp,is_active,is_fiat,search_interval` to include all auxiliary fields. (optional, default: "price,volume,market_cap,circulating_supply,total_supply,quote_timestamp,is_active,is_fiat")
        skip_invalid: Pass `true` to relax request validation rules. When requesting records on multiple cryptocurrencies an error is returned if no match is found for 1 or more requested cryptocurrencies. If set to true, invalid lookups will be skipped allowing valid cryptocurrencies to still be returned. (optional, default: True)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await quotes_historical_v3(symbol="BTC")

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v3/cryptocurrency/quotes/historical"
        params = {
            "id": id,
            "symbol": symbol,
            "time_start": time_start,
            "time_end": time_end,
            "count": count,
            "interval": interval,
            "convert": convert,
            "convert_id": convert_id,
            "aux": aux,
            "skip_invalid": str(skip_invalid).lower()
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in quotes_historical_v3: {e}")
        return {"error": str(e), "endpoint": "/v3/cryptocurrency/quotes/historical"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns a paginated list of all CMC Crypto Fear an"

)
async def cmc_crypto_fear_and_greed_historical(
    context: Context,
    start: int = 1,
    limit: int = 50
) -> Any:
    """
    Returns a paginated list of all CMC Crypto Fear and Greed values at 12am UTC time. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Basic - Startup - Hobbyist - Standard - Professional - Enterprise **Cache / Update frequency:** Every 15 seconds. **Plan credit use:** 1 API call credit per request no matter query size. **CMC equivalent pages:** Our CMC Crypto Fear and Greed Index card on https://coinmarketcap.com/charts/.

    Generated from OpenAPI endpoint: GET /v3/fear-and-greed/historical

    Args:
        context: MCP context (auto-injected by framework, not user-provided)
        start: Optionally offset the start (1-based index) of the paginated list of items to return. (optional, default: 1)
        limit: Optionally specify the number of results to return. Use this parameter and the "start" parameter to determine your own pagination size. (optional, default: 50)

    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await cmc_crypto_fear_and_greed_historical()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v3/fear-and-greed/historical"
        params = {
            "start": start,
            "limit": limit
        }
        params = {k: v for k, v in params.items() if v is not None}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in cmc_crypto_fear_and_greed_historical: {e}")
        return {"error": str(e), "endpoint": "/v3/fear-and-greed/historical"}


@mcp.tool()
@require_payment_for_tool(
    price=TokenAmount(
        amount="50000000000000000",  # 0.05 tokens
        asset=TokenAsset(
            address="0x3e17730bb2ca51a8D5deD7E44c003A2e95a4d822",
            decimals=6,
            network="sepolia",
            eip712=EIP712Domain(
                name="IATPWallet",
                version="1"
            )
        )
    ),
    description="Returns the lastest CMC Crypto Fear and Greed valu"

)
async def cmc_crypto_fear_and_greed_latest(
    context: Context
) -> Any:
    """
    Returns the lastest CMC Crypto Fear and Greed value. **This endpoint is available on the following <a href="https://coinmarketcap.com/api/features" target="_blank">API plans</a>:** - Basic - Startup - Hobbyist - Standard - Professional - Enterprise **Cache / Update frequency:** Every 15 minutes. **Plan credit use:** 1 call credit per request. **CMC equivalent pages:** Our CMC Crypto Fear and Greed Index card on https://coinmarketcap.com/charts/.

    Generated from OpenAPI endpoint: GET /v3/fear-and-greed/latest

    Args:
        context: MCP context (auto-injected by framework, not user-provided)


    Returns:
        API response (dict, list, or other JSON type)

    Example Usage:
        await cmc_crypto_fear_and_greed_latest()

        Note: 'context' parameter is auto-injected by MCP framework
    """
    # Payment already verified by @require_payment_for_tool decorator
    # Get API key using helper (handles request.state fallback)
    api_key = get_active_api_key(context)

    try:
        url = f"https://pro-api.coinmarketcap.com/v3/fear-and-greed/latest"
        params = {}
        headers = {}
        if api_key:
            # Custom header (primary)
            headers["X-CMC_PRO_API_KEY"] = api_key
            # Also send standard formats for robustness
            headers["Authorization"] = f"Bearer {api_key}"
            headers["X-API-Key"] = api_key

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()

        return response.json()

    except Exception as e:
        logger.error(f"Error in cmc_crypto_fear_and_greed_latest: {e}")
        return {"error": str(e), "endpoint": "/v3/fear-and-greed/latest"}


# TODO: Add your API-specific functions here

# ============================================================================
# APPLICATION SETUP WITH STARLETTE MIDDLEWARE
# ============================================================================

def create_app_with_middleware():
    """
    Create Starlette app with d402 payment middleware.
    
    Strategy:
    1. Get FastMCP's Starlette app via streamable_http_app()
    2. Extract payment configs from @require_payment_for_tool decorators
    3. Add Starlette middleware with extracted configs
    4. Single source of truth - no duplication!
    """
    logger.info("🔧 Creating FastMCP app with middleware...")
    
    # Get FastMCP's Starlette app
    app = mcp.streamable_http_app()
    logger.info(f"✅ Got FastMCP Starlette app")
    
    # Extract payment configs from decorators (single source of truth!)
    tool_payment_configs = extract_payment_configs_from_mcp(mcp, SERVER_ADDRESS)
    logger.info(f"📊 Extracted {len(tool_payment_configs)} payment configs from @require_payment_for_tool decorators")
    
    # D402 Configuration
    facilitator_url = os.getenv("FACILITATOR_URL") or os.getenv("D402_FACILITATOR_URL")
    operator_key = os.getenv("MCP_OPERATOR_PRIVATE_KEY")
    network = os.getenv("NETWORK", "sepolia")
    testing_mode = os.getenv("D402_TESTING_MODE", "false").lower() == "true"
    
    # Log D402 configuration with prominent facilitator info
    logger.info("="*60)
    logger.info("D402 Payment Protocol Configuration:")
    logger.info(f"  Server Address: {SERVER_ADDRESS}")
    logger.info(f"  Network: {network}")
    logger.info(f"  Operator Key: {'✅ Set' if operator_key else '❌ Not set'}")
    logger.info(f"  Testing Mode: {'⚠️  ENABLED (bypasses facilitator)' if testing_mode else '✅ DISABLED (uses facilitator)'}")
    logger.info("="*60)
    
    if not facilitator_url and not testing_mode:
        logger.error("❌ FACILITATOR_URL required when testing_mode is disabled!")
        raise ValueError("Set FACILITATOR_URL or enable D402_TESTING_MODE=true")
    
    if facilitator_url:
        logger.info(f"🌐 FACILITATOR: {facilitator_url}")
        if "localhost" in facilitator_url or "127.0.0.1" in facilitator_url or "host.docker.internal" in facilitator_url:
            logger.info(f"   📍 Using LOCAL facilitator for development")
        else:
            logger.info(f"   🌍 Using REMOTE facilitator for production")
    else:
        logger.warning("⚠️  D402 Testing Mode - Facilitator bypassed")
    logger.info("="*60)
    
    # Add CORS middleware first (processes before other middleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allow all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allow all methods
        allow_headers=["*"],  # Allow all headers
        expose_headers=["mcp-session-id"],  # Expose custom headers to browser
    )
    logger.info("✅ Added CORS middleware (allow all origins, expose mcp-session-id)")
    
    # Add D402 payment middleware with extracted configs
    app.add_middleware(
        D402PaymentMiddleware,
        tool_payment_configs=tool_payment_configs,
        server_address=SERVER_ADDRESS,
        requires_auth=True,  # Extracts API keys + checks payment
        internal_api_key=API_KEY,  # Server's internal key (for Mode 2: paid access)
        testing_mode=testing_mode,
        facilitator_url=facilitator_url,
        facilitator_api_key=os.getenv("D402_FACILITATOR_API_KEY"),
        server_name="coinmarketcap-api-mcp-server"  # MCP server ID for tracking
    )
    logger.info("✅ Added D402PaymentMiddleware")
    logger.info("   - Auth extraction: Enabled")
    logger.info("   - Dual mode: API key OR payment")
    
    # Add health check endpoint (bypasses middleware)
    @app.route("/health", methods=["GET"])
    async def health_check(request: Request) -> JSONResponse:
        """Health check endpoint for container orchestration."""
        return JSONResponse(
            content={
                "status": "healthy",
                "service": "coinmarketcap-api-mcp-server",
                "timestamp": datetime.now().isoformat()
            }
        )
    logger.info("✅ Added /health endpoint")
    
    return app

if __name__ == "__main__":
    logger.info("="*80)
    logger.info(f"Starting Coinmarketcap API MCP Server")
    logger.info("="*80)
    logger.info("Architecture:")
    logger.info("  1. D402PaymentMiddleware intercepts requests")
    logger.info("     - Extracts API keys from Authorization header")
    logger.info("     - Checks payment → HTTP 402 if no API key AND no payment")
    logger.info("  2. FastMCP processes valid requests with tool decorators")
    logger.info("="*80)
    
    # Create app with middleware
    app = create_app_with_middleware()
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level=os.getenv("LOG_LEVEL", "info").lower()
    )
