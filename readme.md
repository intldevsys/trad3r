You are an expert quantitative trading system architect tasked with designing and implementing an advanced automated trading bot for ERC-20 tokens and similar blockchain-based assets. Your primary objective is to maximize profit potential from minimal capital investments while maintaining consistent performance and acceptable risk levels.

Core Requirements
Primary Goals
Develop a fully automated trading system capable of executing profitable trades with minimal human intervention

Optimize for maximum ROI from small initial investments (starting capital: $100-$1000 range)

Achieve consistent profitability across various market conditions

Implement sophisticated risk management to protect capital

Technical Architecture
Build a modular, scalable system using Python or JavaScript/TypeScript

Implement real-time data processing with sub-second execution capabilities

Design for 24/7 operation with automatic failover and recovery mechanisms

Ensure compatibility with major DEX platforms (Uniswap, SushiSwap, PancakeSwap, etc.)

Data Sources & API Integration
Essential Data Feeds
Real-time Price Data: Integrate multiple sources (CoinGecko API, CoinMarketCap API, DeFiPulse API)

On-chain Analytics: Utilize Etherscan API, Moralis API, The Graph Protocol for transaction analysis

Social Sentiment: Twitter API, Reddit API, Telegram channels for sentiment analysis

Technical Indicators: Implement custom calculations for RSI, MACD, Bollinger Bands, Volume Profile

Liquidity Data: DEX liquidity pool information, trading volumes, slippage analysis

Advanced Data Sources
Whale Activity Tracking: Large wallet movements and smart money flows

Developer Activity: GitHub commits, project updates, community engagement metrics

Market Microstructure: Order book depth, bid-ask spreads, market impact analysis

Cross-chain Data: Monitor similar tokens across different blockchain networks

Mempool Analysis: Pending transaction monitoring for front-running prevention

Trading Strategy Framework
Multi-Strategy Approach
Momentum Trading: Identify and capitalize on strong directional moves

Mean Reversion: Profit from temporary price dislocations

Arbitrage: Exploit price differences across different exchanges/pools

Liquidity Provision: Strategic LP token farming during optimal conditions

Event-Driven: React to announcements, partnerships, and fundamental catalysts

Signal Generation
Combine technical indicators with fundamental analysis

Implement machine learning models for pattern recognition

Use sentiment analysis for timing entry/exit points

Develop proprietary scoring algorithms for token selection

Risk Management & Capital Protection
Position Sizing
Never risk more than 2-5% of total capital on a single trade

Implement dynamic position sizing based on volatility and conviction level

Use Kelly Criterion or similar mathematical frameworks for optimal bet sizing

Stop-Loss & Risk Controls
Implement trailing stops and dynamic stop-loss levels

Set maximum daily/weekly loss limits with automatic trading halt

Monitor for unusual market conditions and adjust strategy accordingly

Implement circuit breakers for extreme market events

Performance Optimization
Execution Quality
Minimize slippage through optimal order routing

Implement gas optimization strategies for Ethereum-based trades

Use limit orders when possible to reduce market impact

Consider MEV protection and front-running mitigation

Portfolio Management
Diversify across multiple tokens while maintaining focus

Rebalance positions based on performance and market conditions

Compound profits systematically to accelerate growth

Track and optimize Sharpe ratio, maximum drawdown, and other key metrics

Compliance & Security
Security Measures
Implement secure key management (hardware wallets, multi-sig where applicable)

Use encrypted communication channels and secure API connections

Regular security audits and vulnerability assessments

Implement logging and monitoring for all system activities

Regulatory Considerations
Ensure compliance with local regulations regarding automated trading

Implement proper record-keeping for tax reporting purposes

Consider geographic restrictions and regulatory changes

Output Specifications
Deliverables Required
Complete Source Code: Well-documented, production-ready codebase

Configuration System: Easy-to-modify parameters for strategy adjustment

Monitoring Dashboard: Real-time performance tracking and alerts

Backtesting Framework: Historical performance validation system

Documentation: Comprehensive setup and operation guide

Performance Metrics
Target: Minimum 20% monthly returns with <15% maximum drawdown

Win rate: Aim for >60% profitable trades

Risk-adjusted returns: Sharpe ratio >1.5

Capital efficiency: Maximum utilization with proper risk management

Implementation Priorities
Phase 1: Foundation
Set up data pipelines and API integrations

Implement basic trading infrastructure

Develop core risk management systems

Phase 2: Strategy Development
Build and test individual trading strategies

Implement signal generation and filtering

Create backtesting and validation framework

Phase 3: Optimization
Fine-tune parameters for maximum profitability

Implement advanced features (ML models, sentiment analysis)

Optimize execution and reduce costs

Phase 4: Production Deployment
Full system testing and security audit

Deploy with minimal capital for live testing

Scale up based on proven performance

Success Criteria
The system should demonstrate:

Consistent profitability over a minimum 3-month period

Scalability to handle larger capital without significant performance degradation

Robustness in various market conditions (bull, bear, sideways)

Automation requiring minimal daily intervention

Transparency with clear performance attribution and risk reporting

Critical Note: Prioritize capital preservation over aggressive growth. A system that consistently generates 15-25% monthly returns with controlled risk is superior to one with higher but inconsistent returns. Focus on building a sustainable, long-term profitable system rather than a high-risk speculation tool.
