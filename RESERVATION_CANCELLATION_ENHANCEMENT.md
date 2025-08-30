# Reservation Cancellation Enhancement

## Overview
Enhanced the reservation cancellation system to include proper time-based restrictions and configurable policies.

## Previous Implementation
The original `cancel_reservation` function only had basic checks:
- ✅ Past date check
- ✅ Already cancelled check  
- ✅ Completed reservation check

## New Implementation

### ✨ Enhanced Features

#### 1. **Time-Based Restrictions**
- **Minimum Advance Notice**: Configurable minimum hours required before reservation time
- **Same-Day Cancellation Policy**: Configurable option to allow/disallow same-day cancellations
- **Precise Time Calculations**: Uses exact datetime comparison instead of just date comparison

#### 2. **Configurable Settings**
Added new settings in `settings.py`:
```python
RESERVATION_CANCELLATION = {
    'MINIMUM_ADVANCE_HOURS': int(os.getenv('RESERVATION_MIN_CANCEL_HOURS', 24)),
    'ALLOW_SAME_DAY_CANCELLATION': os.getenv('ALLOW_SAME_DAY_CANCEL', 'False').lower() == 'true',
    'EMERGENCY_CONTACT_INFO': os.getenv('RESTAURANT_EMERGENCY_CONTACT', 'Please contact the restaurant directly'),
}
```

#### 3. **Environment Variables**
Added to `.env.example`:
```bash
RESERVATION_MIN_CANCEL_HOURS=24
ALLOW_SAME_DAY_CANCEL=False
RESTAURANT_EMERGENCY_CONTACT=Please contact the restaurant directly for same-day cancellations
```

#### 4. **Utility Functions**
Created `restaurants/utils.py` with reusable functions:
- `can_cancel_reservation(reservation)` - Check if cancellation is allowed
- `get_cancellation_deadline(reservation)` - Calculate cancellation deadline
- `get_reservation_cancellation_info(reservation)` - Get comprehensive cancellation info

#### 5. **New API Endpoints**

##### Get Cancellation Information
```
GET /api/restaurants/reservations/{id}/cancellation-info/
```
Returns:
```json
{
    "can_cancel": true,
    "reason": "Reservation can be cancelled",
    "cancellation_deadline": "2024-01-15T18:00:00Z",
    "policy": {
        "minimum_advance_hours": 24,
        "allow_same_day_cancellation": false,
        "emergency_contact_info": "Please contact the restaurant directly"
    }
}
```

#### 6. **Enhanced Reservation Details**
The `reservation_detail` endpoint now includes cancellation information for customers:
```json
{
    "id": 123,
    "restaurant": {...},
    "cancellation_info": {
        "can_cancel": true,
        "reason": "Reservation can be cancelled",
        "cancellation_deadline": "2024-01-15T18:00:00Z",
        "policy": {...}
    }
}
```

#### 7. **Improved Error Messages**
More informative error messages with specific details:
```json
{
    "error": "Cannot cancel reservation. Minimum 24 hours advance notice required. Only 12.5 hours remaining until your reservation. Please contact the restaurant directly"
}
```

#### 8. **Status Tracking**
Enhanced cancellation tracking with `ReservationStatusUpdate` records:
- Records who cancelled the reservation
- Tracks advance notice given
- Stores cancellation notes

## Business Rules Implemented

### Default Policy (Configurable)
- **Minimum Advance Notice**: 24 hours
- **Same-Day Cancellations**: Not allowed
- **Past Reservations**: Cannot be cancelled
- **Already Cancelled**: Cannot be cancelled again
- **Completed Reservations**: Cannot be cancelled

### Flexible Configuration
Restaurants can customize their cancellation policy by setting environment variables:

#### Strict Policy Example:
```bash
RESERVATION_MIN_CANCEL_HOURS=48
ALLOW_SAME_DAY_CANCEL=False
```

#### Lenient Policy Example:
```bash
RESERVATION_MIN_CANCEL_HOURS=2
ALLOW_SAME_DAY_CANCEL=True
```

## API Usage Examples

### Check if Reservation Can Be Cancelled
```bash
curl -X GET "http://localhost:8000/api/restaurants/reservations/123/cancellation-info/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Cancel a Reservation
```bash
curl -X POST "http://localhost:8000/api/restaurants/reservations/123/cancel/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Testing
Comprehensive test suite in `restaurants/test_cancellation.py` covering:
- ✅ Sufficient advance notice scenarios
- ✅ Insufficient advance notice scenarios  
- ✅ Same-day cancellation (enabled/disabled)
- ✅ Past reservation attempts
- ✅ Already cancelled reservations
- ✅ Completed reservations
- ✅ Cancellation deadline calculations

## Benefits

### For Customers
- **Clear Expectations**: Know exactly when they can/cannot cancel
- **Helpful Error Messages**: Understand why cancellation failed
- **Advance Planning**: See cancellation deadline in reservation details

### For Restaurants
- **Configurable Policies**: Set cancellation rules that fit their business
- **Better Planning**: Reduce last-minute cancellations
- **Customer Communication**: Provide emergency contact information

### For Developers
- **Reusable Code**: Utility functions can be used throughout the application
- **Maintainable**: Centralized business logic
- **Testable**: Comprehensive test coverage

## Migration Notes
- No database migrations required
- Backward compatible with existing reservations
- Environment variables are optional (sensible defaults provided)
- Existing API endpoints remain unchanged (only enhanced)

## Future Enhancements
- **Restaurant-Specific Policies**: Different rules per restaurant
- **Time-of-Day Rules**: Different policies for peak/off-peak hours
- **Cancellation Fees**: Integration with payment system for cancellation charges
- **Automated Reminders**: Send cancellation deadline reminders to customers