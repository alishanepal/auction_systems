# Proxy Bidding System Documentation

## Overview

The Proxy Bidding System is an advanced feature that allows users to set a maximum bid amount for auctions, and the system automatically bids the minimum required amount to stay ahead of other bidders, up to the user's maximum limit. This system uses a **Greedy Algorithm** to optimize bidding strategy.

## Features

### 🎯 **Core Functionality**
- **Automatic Bidding**: System automatically places bids on behalf of users
- **Maximum Limit Protection**: Never exceeds the user's set maximum amount
- **Greedy Algorithm**: Optimizes bid amounts to stay ahead efficiently
- **Real-time Processing**: Responds immediately to new bids
- **Editable Proxy Bids**: Users can modify or remove their proxy bids anytime

### 🔄 **Integration Points**
- **Live Auctions**: Proxy bids activate when auctions go live
- **Manual Bidding**: Proxy bids trigger when other users place manual bids
- **Upcoming Auctions**: Proxy bids can be set before auctions start
- **Real-time Updates**: WebSocket integration for live updates

## How It Works

### 1. **Setting Proxy Bids**
```python
# User sets a maximum bid amount
ProxyBiddingSystem.set_proxy_bid(
    bidder_id=user_id,
    auction_id=auction_id,
    product_id=product_id,
    max_amount=500.0
)
```

### 2. **Greedy Algorithm Implementation**
The system uses a greedy approach to determine optimal bid amounts:

```python
# Calculate minimum bid needed to become highest bidder
minimum_bid_needed = current_highest_amount + calculate_minimum_increment(current_highest_amount)

# Use greedy strategy: bid minimum needed + one increment to discourage others
optimal_bid_amount = min(max_amount, minimum_bid_needed + calculate_minimum_increment(minimum_bid_needed))
```

### 3. **Automatic Execution**
- **When auction goes live**: All proxy bids are processed immediately
- **When new bid is placed**: Proxy bids are triggered to respond
- **Real-time updates**: WebSocket broadcasts proxy bid executions

## Database Schema

### BidderMinimumAmount Table
```sql
CREATE TABLE bidder_minimum_amounts (
    id INTEGER PRIMARY KEY,
    bidder_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    auction_id INTEGER NOT NULL,
    minimum_amount FLOAT NOT NULL,
    created_at DATETIME,
    updated_at DATETIME,
    FOREIGN KEY (bidder_id) REFERENCES users(id),
    FOREIGN KEY (product_id) REFERENCES products(id),
    FOREIGN KEY (auction_id) REFERENCES auctions(id),
    UNIQUE(bidder_id, auction_id)
);
```

## API Endpoints

### 1. **Set Proxy Bid**
```http
POST /api/proxy-bid/set
Content-Type: application/x-www-form-urlencoded

auction_id=123&max_amount=500.0
```

**Response:**
```json
{
    "success": true,
    "message": "Proxy bid of 500.0 set successfully for upcoming auction",
    "proxy_amount": 500.0
}
```

### 2. **Get Proxy Bid Status**
```http
GET /api/proxy-bid/get/{auction_id}
```

**Response:**
```json
{
    "success": true,
    "has_proxy": true,
    "proxy_amount": 500.0,
    "current_highest_bid": 450.0,
    "is_winning": true,
    "remaining_budget": 50.0,
    "auction_status": "live"
}
```

### 3. **Remove Proxy Bid**
```http
POST /api/proxy-bid/remove/{auction_id}
```

**Response:**
```json
{
    "success": true,
    "message": "Proxy bid removed successfully"
}
```

### 4. **Get All Proxy Bids**
```http
GET /api/proxy-bid/all
```

**Response:**
```json
{
    "success": true,
    "proxy_bids": [
        {
            "auction_id": 123,
            "product_name": "iPhone 15",
            "proxy_amount": 500.0,
            "current_highest_bid": 450.0,
            "auction_status": "live",
            "is_winning": true,
            "created_at": "2024-01-01T10:00:00",
            "updated_at": "2024-01-01T10:30:00"
        }
    ]
}
```

## Usage Examples

### 1. **Setting Proxy Bid for Upcoming Auction**
```javascript
// User sets proxy bid before auction starts
const formData = new FormData();
formData.append('auction_id', '123');
formData.append('max_amount', '500.0');

fetch('/api/proxy-bid/set', {
    method: 'POST',
    body: formData
})
.then(response => response.json())
.then(data => {
    if (data.success) {
        console.log('Proxy bid set successfully');
    }
});
```

### 2. **Real-time Proxy Bid Execution**
```javascript
// Listen for proxy bid executions via WebSocket
socket.on('proxy_bids_executed', function(data) {
    console.log('Proxy bids executed:', data.proxy_bids);
    // Update UI to show automatic bids
});
```

### 3. **Managing Proxy Bids**
```javascript
// Edit existing proxy bid
function editProxyBid() {
    // Load current proxy amount
    fetch(`/api/proxy-bid/get/${auctionId}`)
        .then(response => response.json())
        .then(data => {
            if (data.has_proxy) {
                document.getElementById('max-amount').value = data.proxy_amount;
            }
        });
}

// Remove proxy bid
function removeProxyBid() {
    fetch(`/api/proxy-bid/remove/${auctionId}`, {
        method: 'POST'
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            console.log('Proxy bid removed');
        }
    });
}
```

## Algorithm Details

### Greedy Strategy
1. **Calculate Minimum Required**: Determine the minimum bid needed to become the highest bidder
2. **Optimize Bid Amount**: Add one increment to discourage other bidders
3. **Respect Maximum Limit**: Never exceed the user's maximum amount
4. **Immediate Response**: Execute proxy bids as soon as conditions are met

### Bid Increment Calculation
```python
def calculate_minimum_increment(current_bid):
    if current_bid < 100:
        return 1
    elif current_bid < 1000:
        return 5
    elif current_bid < 10000:
        return 10
    else:
        return ceil(current_bid * 0.01)  # 1% for higher amounts
```

## Security Features

### 1. **Validation**
- Maximum amount must be higher than current highest bid
- Users cannot set proxy bids on their own auctions
- Auction must be active (not ended)

### 2. **Rate Limiting**
- Proxy bids are processed sequentially to prevent race conditions
- Database transactions ensure data consistency

### 3. **User Authentication**
- All proxy bid operations require user authentication
- Role-based access control (bidders only)

## Performance Considerations

### 1. **Database Optimization**
- Indexed foreign keys for fast lookups
- Unique constraint prevents duplicate proxy bids
- Efficient queries for proxy bid processing

### 2. **Real-time Processing**
- WebSocket integration for immediate updates
- Background task for auction status monitoring
- Optimized proxy bid execution algorithm

### 3. **Scalability**
- Stateless proxy bidding system
- Modular design for easy extension
- Efficient memory usage

## Testing

### Running Tests
```bash
# Test proxy bidding functionality
python test_proxy_bidding.py

# Test individual components
python -c "from app.proxy_bidding import ProxyBiddingSystem; print('Proxy bidding system loaded successfully')"
```

### Test Scenarios
1. **Upcoming Auction**: Set proxy bids before auction starts
2. **Live Auction**: Proxy bids activate when auction goes live
3. **Manual Bid Response**: Proxy bids respond to manual bids
4. **Multiple Bidders**: Competition between multiple proxy bids
5. **Edge Cases**: Maximum limits, auction ending, etc.

## Integration with Existing System

### 1. **Socket Events**
- Proxy bids integrate with existing WebSocket system
- Real-time updates for all auction participants
- Automatic processing when auctions change status

### 2. **API Integration**
- Extends existing bidding API
- Maintains compatibility with manual bidding
- Seamless integration with auction management

### 3. **Database Integration**
- Uses existing `BidderMinimumAmount` table
- Integrates with existing `Bid` and `Auction` models
- Maintains data consistency across all operations

## Future Enhancements

### 1. **Advanced Algorithms**
- Machine learning for bid prediction
- Dynamic maximum amount adjustment
- Multi-auction proxy bidding strategies

### 2. **User Experience**
- Proxy bid analytics and insights
- Bid history visualization
- Smart recommendations for maximum amounts

### 3. **Performance**
- Caching for frequently accessed data
- Batch processing for multiple auctions
- Optimized database queries

## Troubleshooting

### Common Issues

1. **Proxy Bid Not Executing**
   - Check auction status (must be live)
   - Verify maximum amount is sufficient
   - Ensure user is not the current highest bidder

2. **Database Errors**
   - Check foreign key constraints
   - Verify unique constraint on bidder/auction combination
   - Ensure proper transaction handling

3. **Real-time Updates Not Working**
   - Check WebSocket connection
   - Verify auction room subscription
   - Check background task status

### Debug Mode
```python
import logging
logging.getLogger('app.proxy_bidding').setLevel(logging.DEBUG)
```

## Conclusion

The Proxy Bidding System provides a powerful, automated bidding solution that enhances user experience while maintaining system integrity. The greedy algorithm ensures optimal bidding strategies, while the real-time integration keeps all users informed of auction developments.

The system is designed to be scalable, secure, and user-friendly, making it an essential feature for any modern auction platform.

