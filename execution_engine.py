"""
Execution Engine for Crypto Trading Bot
Handles order routing, execution optimization, and DEX interactions.
"""

import logging
import time
import asyncio
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import json
from decimal import Decimal
from web3 import Web3
from eth_account import Account
import ccxt

from ..utils.config_manager import get_config
from ..risk_management.risk_manager import Position

logger = logging.getLogger(__name__)


class OrderType(Enum):
    """Order type enumeration."""
    MARKET = "market"
    LIMIT = "limit"
    STOP_LOSS = "stop_loss"
    TAKE_PROFIT = "take_profit"


class OrderStatus(Enum):
    """Order status enumeration."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    FAILED = "failed"


class GasStrategy(Enum):
    """Gas pricing strategy enumeration."""
    SLOW = "slow"
    STANDARD = "standard"
    FAST = "fast"
    FASTEST = "fastest"


@dataclass
class Order:
    """Represents a trading order."""
    id: str
    symbol: str
    side: str  # "buy" or "sell"
    order_type: OrderType
    quantity: float
    price: Optional[float] = None
    status: OrderStatus = OrderStatus.PENDING
    timestamp: datetime = None
    filled_quantity: float = 0.0
    average_price: float = 0.0
    fees: float = 0.0
    gas_used: Optional[int] = None
    tx_hash: Optional[str] = None
    exchange: Optional[str] = None
    strategy: Optional[str] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()


@dataclass
class ExecutionResult:
    """Result of order execution."""
    success: bool
    order: Order
    message: str
    execution_time: float
    slippage: float = 0.0
    gas_cost: float = 0.0


class GasManager:
    """Manages gas pricing and optimization."""
    
    def __init__(self, web3: Web3):
        self.web3 = web3
        self.config = get_config()
        self.max_gas_price = self.config.execution.max_gas_price_gwei * 10**9  # Convert to wei
        
    def get_gas_price(self, strategy: GasStrategy = GasStrategy.FAST) -> int:
        """Get gas price based on strategy."""
        try:
            # Get current gas price from network
            current_gas_price = self.web3.eth.gas_price
            
            # Apply strategy multiplier
            multipliers = {
                GasStrategy.SLOW: 0.8,
                GasStrategy.STANDARD: 1.0,
                GasStrategy.FAST: 1.2,
                GasStrategy.FASTEST: 1.5
            }
            
            gas_price = int(current_gas_price * multipliers[strategy])
            
            # Cap at maximum
            gas_price = min(gas_price, self.max_gas_price)
            
            logger.debug(f"Gas price for {strategy.value}: {gas_price / 10**9:.2f} Gwei")
            return gas_price
            
        except Exception as e:
            logger.error(f"Error getting gas price: {e}")
            # Fallback to default
            return 20 * 10**9  # 20 Gwei
    
    def estimate_gas_cost(self, gas_limit: int, gas_price: int) -> float:
        """Estimate gas cost in USD."""
        # Simplified calculation - would need ETH/USD price
        eth_price = 2000  # Placeholder
        gas_cost_eth = (gas_limit * gas_price) / 10**18
        return gas_cost_eth * eth_price


class DEXConnector:
    """Base class for DEX connectors."""
    
    def __init__(self, name: str):
        self.name = name
        self.config = get_config()
    
    async def get_quote(self, token_in: str, token_out: str, amount_in: float) -> Dict[str, Any]:
        """Get quote for a swap."""
        raise NotImplementedError
    
    async def execute_swap(self, order: Order) -> ExecutionResult:
        """Execute a swap order."""
        raise NotImplementedError
    
    def get_liquidity(self, token_pair: str) -> Dict[str, float]:
        """Get liquidity information for a token pair."""
        raise NotImplementedError


class UniswapV3Connector(DEXConnector):
    """Uniswap V3 connector."""
    
    def __init__(self, web3: Web3):
        super().__init__("uniswap_v3")
        self.web3 = web3
        self.router_address = "0xE592427A0AEce92De3Edee1F18E0157C05861564"  # Uniswap V3 Router
        
        # Load contract ABI (simplified)
        self.router_abi = []  # Would load actual ABI
        
    async def get_quote(self, token_in: str, token_out: str, amount_in: float) -> Dict[str, Any]:
        """Get quote from Uniswap V3."""
        try:
            # Simplified quote calculation
            # In practice, would call quoter contract
            
            # Mock quote for demonstration
            quote = {
                "amount_out": amount_in * 0.999,  # Assume 0.1% slippage
                "price_impact": 0.001,
                "gas_estimate": 150000,
                "route": [token_in, token_out],
                "exchange": self.name
            }
            
            logger.debug(f"Uniswap V3 quote: {amount_in} {token_in} -> {quote['amount_out']} {token_out}")
            return quote
            
        except Exception as e:
            logger.error(f"Error getting Uniswap V3 quote: {e}")
            return {}
    
    async def execute_swap(self, order: Order) -> ExecutionResult:
        """Execute swap on Uniswap V3."""
        start_time = time.time()
        
        try:
            # Simplified execution - would build and send actual transaction
            
            # Simulate transaction
            await asyncio.sleep(0.1)  # Simulate network delay
            
            # Mock successful execution
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.average_price = order.price or 1.0
            order.tx_hash = "0x" + "a" * 64  # Mock transaction hash
            order.gas_used = 150000
            
            execution_time = time.time() - start_time
            
            result = ExecutionResult(
                success=True,
                order=order,
                message="Order executed successfully on Uniswap V3",
                execution_time=execution_time,
                slippage=0.001,
                gas_cost=0.05
            )
            
            logger.info(f"Uniswap V3 execution successful: {order.symbol}, {order.quantity}")
            return result
            
        except Exception as e:
            logger.error(f"Uniswap V3 execution failed: {e}")
            
            order.status = OrderStatus.FAILED
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                success=False,
                order=order,
                message=f"Execution failed: {str(e)}",
                execution_time=execution_time
            )


class SushiSwapConnector(DEXConnector):
    """SushiSwap connector."""
    
    def __init__(self, web3: Web3):
        super().__init__("sushiswap")
        self.web3 = web3
        self.router_address = "0xd9e1cE17f2641f24aE83637ab66a2cca9C378B9F"  # SushiSwap Router
    
    async def get_quote(self, token_in: str, token_out: str, amount_in: float) -> Dict[str, Any]:
        """Get quote from SushiSwap."""
        try:
            # Mock quote for demonstration
            quote = {
                "amount_out": amount_in * 0.998,  # Assume 0.2% slippage
                "price_impact": 0.002,
                "gas_estimate": 120000,
                "route": [token_in, token_out],
                "exchange": self.name
            }
            
            logger.debug(f"SushiSwap quote: {amount_in} {token_in} -> {quote['amount_out']} {token_out}")
            return quote
            
        except Exception as e:
            logger.error(f"Error getting SushiSwap quote: {e}")
            return {}
    
    async def execute_swap(self, order: Order) -> ExecutionResult:
        """Execute swap on SushiSwap."""
        start_time = time.time()
        
        try:
            # Simulate execution
            await asyncio.sleep(0.1)
            
            order.status = OrderStatus.FILLED
            order.filled_quantity = order.quantity
            order.average_price = order.price or 1.0
            order.tx_hash = "0x" + "b" * 64
            order.gas_used = 120000
            
            execution_time = time.time() - start_time
            
            result = ExecutionResult(
                success=True,
                order=order,
                message="Order executed successfully on SushiSwap",
                execution_time=execution_time,
                slippage=0.002,
                gas_cost=0.04
            )
            
            logger.info(f"SushiSwap execution successful: {order.symbol}, {order.quantity}")
            return result
            
        except Exception as e:
            logger.error(f"SushiSwap execution failed: {e}")
            
            order.status = OrderStatus.FAILED
            execution_time = time.time() - start_time
            
            return ExecutionResult(
                success=False,
                order=order,
                message=f"Execution failed: {str(e)}",
                execution_time=execution_time
            )


class OrderRouter:
    """Smart order routing system."""
    
    def __init__(self, connectors: List[DEXConnector]):
        self.connectors = {connector.name: connector for connector in connectors}
        self.config = get_config()
        self.min_liquidity = self.config.execution.order_routing.get("min_liquidity_usd", 10000)
        self.max_splits = self.config.execution.order_routing.get("max_splits", 5)
    
    async def find_best_route(self, token_in: str, token_out: str, amount_in: float) -> Dict[str, Any]:
        """Find the best execution route across DEXs."""
        quotes = {}
        
        # Get quotes from all connectors
        for name, connector in self.connectors.items():
            try:
                quote = await connector.get_quote(token_in, token_out, amount_in)
                if quote:
                    quotes[name] = quote
            except Exception as e:
                logger.error(f"Error getting quote from {name}: {e}")
        
        if not quotes:
            return {}
        
        # Find best quote based on amount out and gas costs
        best_route = None
        best_net_amount = 0
        
        for exchange, quote in quotes.items():
            # Calculate net amount after gas costs
            gas_cost_usd = quote.get("gas_estimate", 0) * 20e-9 * 2000  # Simplified
            net_amount = quote["amount_out"] - gas_cost_usd
            
            if net_amount > best_net_amount:
                best_net_amount = net_amount
                best_route = {
                    "exchange": exchange,
                    "quote": quote,
                    "net_amount": net_amount
                }
        
        logger.info(f"Best route: {best_route['exchange']} with net amount {best_net_amount:.6f}")
        return best_route
    
    async def split_order(self, token_in: str, token_out: str, total_amount: float) -> List[Dict[str, Any]]:
        """Split large order across multiple DEXs for better execution."""
        if total_amount < self.min_liquidity:
            # Small order, use single route
            route = await self.find_best_route(token_in, token_out, total_amount)
            return [route] if route else []
        
        # For large orders, split across multiple DEXs
        splits = []
        remaining_amount = total_amount
        split_size = total_amount / min(self.max_splits, len(self.connectors))
        
        for i in range(min(self.max_splits, len(self.connectors))):
            if remaining_amount <= 0:
                break
            
            amount = min(split_size, remaining_amount)
            route = await self.find_best_route(token_in, token_out, amount)
            
            if route:
                route["amount"] = amount
                splits.append(route)
                remaining_amount -= amount
        
        logger.info(f"Split order into {len(splits)} parts")
        return splits


class ExecutionEngine:
    """Main execution engine."""
    
    def __init__(self):
        self.config = get_config()
        
        # Initialize Web3 connection
        self.web3 = Web3(Web3.HTTPProvider("https://mainnet.infura.io/v3/YOUR_PROJECT_ID"))
        
        # Initialize gas manager
        self.gas_manager = GasManager(self.web3)
        
        # Initialize DEX connectors
        self.connectors = [
            UniswapV3Connector(self.web3),
            SushiSwapConnector(self.web3)
        ]
        
        # Initialize order router
        self.order_router = OrderRouter(self.connectors)
        
        # Order tracking
        self.active_orders: Dict[str, Order] = {}
        self.order_history: List[Order] = []
        
        # Execution settings
        self.slippage_tolerance = self.config.execution.slippage_tolerance_pct / 100
        self.deadline_minutes = self.config.execution.deadline_minutes
        
        logger.info("Execution Engine initialized")
    
    async def execute_order(self, order: Order) -> ExecutionResult:
        """Execute a trading order."""
        logger.info(f"Executing order: {order.id}, {order.symbol}, {order.side}, {order.quantity}")
        
        # Add to active orders
        self.active_orders[order.id] = order
        
        try:
            # Determine token pair
            token_in, token_out = self._parse_symbol(order.symbol, order.side)
            amount_in = order.quantity
            
            # Find best execution route
            if order.order_type == OrderType.MARKET:
                route = await self.order_router.find_best_route(token_in, token_out, amount_in)
                
                if not route:
                    raise Exception("No execution route found")
                
                # Execute on best exchange
                connector = self.connectors[route["exchange"]]
                result = await connector.execute_swap(order)
                
            elif order.order_type == OrderType.LIMIT:
                # For limit orders, would implement order book monitoring
                result = await self._execute_limit_order(order)
                
            else:
                raise Exception(f"Unsupported order type: {order.order_type}")
            
            # Update order tracking
            if result.success:
                order.status = OrderStatus.FILLED
                self.order_history.append(order)
            else:
                order.status = OrderStatus.FAILED
            
            # Remove from active orders
            if order.id in self.active_orders:
                del self.active_orders[order.id]
            
            logger.info(f"Order execution completed: {order.id}, success: {result.success}")
            return result
            
        except Exception as e:
            logger.error(f"Order execution failed: {order.id}, error: {e}")
            
            order.status = OrderStatus.FAILED
            if order.id in self.active_orders:
                del self.active_orders[order.id]
            
            return ExecutionResult(
                success=False,
                order=order,
                message=f"Execution failed: {str(e)}",
                execution_time=0.0
            )
    
    async def _execute_limit_order(self, order: Order) -> ExecutionResult:
        """Execute a limit order (simplified implementation)."""
        # In practice, would monitor order books and execute when price is reached
        logger.info(f"Limit order monitoring not fully implemented: {order.id}")
        
        # For now, treat as market order
        order.order_type = OrderType.MARKET
        return await self.execute_order(order)
    
    def _parse_symbol(self, symbol: str, side: str) -> Tuple[str, str]:
        """Parse trading symbol to determine token pair."""
        # Simplified parsing - assumes format like "ETH/USDC"
        if "/" in symbol:
            base, quote = symbol.split("/")
            if side == "buy":
                return quote, base  # Buying base with quote
            else:
                return base, quote  # Selling base for quote
        else:
            # Default to USDC pair
            if side == "buy":
                return "USDC", symbol
            else:
                return symbol, "USDC"
    
    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an active order."""
        if order_id in self.active_orders:
            order = self.active_orders[order_id]
            order.status = OrderStatus.CANCELLED
            del self.active_orders[order_id]
            self.order_history.append(order)
            
            logger.info(f"Order cancelled: {order_id}")
            return True
        
        logger.warning(f"Order not found for cancellation: {order_id}")
        return False
    
    def get_order_status(self, order_id: str) -> Optional[Order]:
        """Get status of an order."""
        if order_id in self.active_orders:
            return self.active_orders[order_id]
        
        # Check history
        for order in self.order_history:
            if order.id == order_id:
                return order
        
        return None
    
    def get_active_orders(self) -> List[Order]:
        """Get all active orders."""
        return list(self.active_orders.values())
    
    def get_order_history(self, limit: int = 100) -> List[Order]:
        """Get order history."""
        return self.order_history[-limit:]
    
    async def execute_stop_loss(self, position: Position, current_price: float) -> ExecutionResult:
        """Execute stop-loss order for a position."""
        logger.warning(f"Executing stop-loss for {position.symbol} at {current_price}")
        
        # Create stop-loss order
        order = Order(
            id=f"sl_{position.symbol}_{int(time.time())}",
            symbol=position.symbol,
            side="sell" if position.size > 0 else "buy",
            order_type=OrderType.STOP_LOSS,
            quantity=abs(position.size),
            price=current_price
        )
        
        return await self.execute_order(order)
    
    def calculate_slippage(self, expected_price: float, actual_price: float) -> float:
        """Calculate slippage percentage."""
        if expected_price == 0:
            return 0.0
        return abs(actual_price - expected_price) / expected_price * 100
    
    def get_execution_stats(self) -> Dict[str, Any]:
        """Get execution statistics."""
        if not self.order_history:
            return {}
        
        filled_orders = [o for o in self.order_history if o.status == OrderStatus.FILLED]
        
        total_orders = len(self.order_history)
        successful_orders = len(filled_orders)
        success_rate = successful_orders / total_orders * 100 if total_orders > 0 else 0
        
        total_fees = sum(o.fees for o in filled_orders)
        avg_execution_time = sum(getattr(o, 'execution_time', 0) for o in filled_orders) / len(filled_orders) if filled_orders else 0
        
        return {
            "total_orders": total_orders,
            "successful_orders": successful_orders,
            "success_rate": success_rate,
            "total_fees": total_fees,
            "average_execution_time": avg_execution_time,
            "active_orders": len(self.active_orders)
        }
    
    def cleanup(self) -> None:
        """Cleanup resources."""
        # Cancel all active orders
        for order_id in list(self.active_orders.keys()):
            asyncio.create_task(self.cancel_order(order_id))
        
        logger.info("Execution Engine cleaned up")

