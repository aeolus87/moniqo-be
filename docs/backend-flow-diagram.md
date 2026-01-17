# AI Flow Diagram

This diagram shows the complete AI-powered trading flow from creation to execution to monitoring, including swarm coordination.

flowchart TB
    Start[User Creates Trading Flow] --> CreateFlow[Create Trading Flow<br>POST api flows<br>Configure mode trigger agents]

    CreateFlow --> ConfigFlow[Configure Flow<br>Mode solo or swarm<br>Trigger manual or schedule<br>Agents user node ids]

    ConfigFlow --> FlowReady[Flow Ready<br>Status active]
    FlowReady --> WaitTrigger[Wait for Trigger Event]
    WaitTrigger --> Trigger{Flow Trigger}

    Trigger -->|Manual| ManualTrigger[User Triggers Flow<br>POST api flows trigger]
    Trigger -->|Scheduled| CronTrigger[Cron Job Triggers Flow]

    ManualTrigger --> ExecStart[Create Execution Record<br>Status running]
    CronTrigger --> ExecStart

    ExecStart --> FetchData[Fetch OHLCV Data<br>Calculate Indicators SMA RSI MACD]

    FetchData --> FlowMode{Flow Mode}

    FlowMode -->|Solo| MarketAnalysis[Market Analysis<br>Single AI Agent]
    FlowMode -->|Swarm| CreateConversation[Create AI Conversation Log]

    CreateConversation --> ParallelAgents[Parallel Agent Analysis]

    ParallelAgents --> Agent1[Agent 1 Market Analyst]
    ParallelAgents --> Agent2[Agent 2 Risk Guardian]
    ParallelAgents --> Agent3[Agent N Additional Agents]

    Agent1 --> LogMessage1[Log Agent Message]
    Agent2 --> LogMessage2[Log Agent Message]
    Agent3 --> LogMessage3[Log Agent Message]

    LogMessage1 --> CollectVotes[Collect Agent Votes<br>WebSocket Stream]
    LogMessage2 --> CollectVotes
    LogMessage3 --> CollectVotes

    CollectVotes --> CalculateConsensus[Calculate Swarm Consensus]
    CalculateConsensus --> ConsensusResult{Consensus Reached}

    ConsensusResult -->|No| RejectTrade[Reject Trade<br>Status failed]
    ConsensusResult -->|Yes| SwarmDecision[Swarm Decision<br>Buy Sell or Hold]

    SwarmDecision --> AIDecision
    MarketAnalysis --> AIDecision[AI Decision]

    AIDecision --> LogDecision[Log AI Decision]
    LogDecision --> RiskCheck[Risk Check]

    RiskCheck --> CheckLimits[Check User Limits]
    CheckLimits --> LimitsResult{Limits OK}

    LimitsResult -->|Fail| RejectTrade
    LimitsResult -->|Pass| CheckRules[Check Risk Rules]

    CheckRules --> RiskDecision{Risk Decision}

    RiskDecision -->|Fail| RejectTrade
    RiskDecision -->|Warning| ReduceSize[Reduce Position Size]
    RiskDecision -->|Pass| ExecuteTrade[Execute Trade]

    ReduceSize --> ExecuteTrade

    ExecuteTrade --> DecryptCreds[Decrypt Wallet Credentials]
    DecryptCreds --> ConnectExchange[Connect Exchange API]

    ConnectExchange --> PlaceOrder[Place Order]
    PlaceOrder --> OrderFilled{Order Filled}

    OrderFilled -->|No| RetryDecision{Retry Remaining}
    RetryDecision -->|Yes| PlaceOrder
    RetryDecision -->|No| CancelOrder[Cancel Order<br>Status failed]

    CancelOrder --> CompleteExec[Complete Execution]

    OrderFilled -->|Yes| CreatePosition[Create Position Record]

    CreatePosition --> StoreEntry[Store Entry Data]
    StoreEntry --> InitState[Initialize Position State]
    InitState --> SetStops[Set Stop Loss and Take Profit]

    SetStops --> CreateTrans[Create Transaction]
    CreateTrans --> UpdateWallet[Update Wallet State]

    UpdateWallet --> MonitorStart[Start Monitoring]
    MonitorStart --> MonitorLoop[Monitoring Loop]

    MonitorLoop --> FetchPrice[Fetch Market Price]
    FetchPrice --> FetchSentiment[Fetch Sentiment Data]

    FetchSentiment --> CalcPnL[Calculate Unrealized PnL]
    CalcPnL --> UpdatePosition[Update Position]

    UpdatePosition --> AIReeval[AI Re Evaluates Position]
    AIReeval --> CheckExit{Exit Condition}

    CheckExit -->|No| AdjustStops[Adjust Stops]
    AdjustStops --> MonitorLoop

    CheckExit -->|Exit| ClosePosition[Close Position]
    ClosePosition --> PlaceCloseOrder[Place Close Order]

    PlaceCloseOrder --> OrderFilled2{Order Filled}
    OrderFilled2 -->|No| RetryCloseDecision{Retry Remaining}
    RetryCloseDecision -->|Yes| PlaceCloseOrder
    RetryCloseDecision -->|No| ForceClose[Force Close Market Order]

    ForceClose --> UpdatePosition2[Update Position Closed]
    OrderFilled2 -->|Yes| UpdatePosition2

    UpdatePosition2 --> CalcRealized[Calculate Realized PnL]
    CalcRealized --> CreateTrans2[Create Exit Transaction]
    CreateTrans2 --> UpdateWallet2[Update Wallet]

    UpdateWallet2 --> RecordLearning[Record Learning Outcome]
    RecordLearning --> CompleteExec[Complete Execution]

    CompleteExec --> UpdateFlowStats[Update Flow Statistics]
    UpdateFlowStats --> EndCycle[Trading Cycle Complete]

    EndCycle --> WaitTrigger
    RejectTrade --> CompleteExec


## Flow Modes

### Solo Mode
- Single AI agent analyzes market and makes decision
- Direct flow: Fetch Data → Market Analysis → Risk Check → Execute

### Swarm Mode
- Multiple AI agents analyze in parallel
- Each agent logs analysis and vote to conversation
- Consensus calculated from all votes
- Real-time streaming via WebSocket
- Learning outcomes recorded after execution

## Swarm Coordination Details

### Agent Conversation Flow
1. **Create Conversation Log** - Initialize conversation record for execution
2. **Parallel Agent Analysis** - All agents analyze market data simultaneously
3. **Log Agent Messages** - Each agent logs their analysis, vote, and reasoning
4. **Collect Votes** - Gather all agent votes with confidence scores
5. **Calculate Consensus** - Apply voting algorithm (majority vote + weighted confidence)
6. **Stream Updates** - Real-time updates via WebSocket to UI
7. **Execute Consensus Decision** - Use swarm decision for trade execution

### Learning & Feedback
- After position closes, record outcome (success, P&L, time held)
- Update agent performance metrics
- Store lessons learned for future decisions
- Adjust agent parameters based on outcomes
