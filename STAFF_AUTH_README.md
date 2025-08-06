# Staff Authentication System

This document describes the enhanced staff authentication system for chefs, waiters, managers, and other restaurant staff.

## Overview

The system provides role-based authentication and authorization for restaurant staff members with the following features:

- **Role-based login** with specific capabilities for each role
- **Shift management** with clock in/out functionality
- **Profile management** for staff members
- **Permission-based access control** for different restaurant operations

## Staff Roles

### Chef
- Can view and update order status
- Can view menu items
- Can manage kitchen operations
- Cannot manage tables or reservations
- Cannot create other staff members

### Waiter
- Can view and update order status
- Can view menu items
- Can view and manage reservations
- Can manage tables
- Cannot manage kitchen operations
- Cannot create other staff members

### Manager
- Full access to all restaurant operations
- Can create and manage other staff members (except other managers)
- Can manage menu items and categories
- Can view all orders, reservations, and tables
- Can create and manage staff shifts

### Employee
- Basic access to view orders and menu
- Can view reservations
- Cannot update order status
- Cannot manage tables or create staff

## API Endpoints

### Staff Authentication

#### Staff Login
```
POST /api/accounts/staff/login/
```
**Body:**
```json
{
    "phone": "1234567890",
    "password": "password123"
}
```

**Response:**
```json
{
    "success": "Staff login successful",
    "access": "jwt_access_token",
    "refresh": "jwt_refresh_token",
    "access_token_lifetime": 60,
    "user": {
        "id": 1,
        "phone": "1234567890",
        "first_name": "John",
        "last_name": "Chef",
        "is_staff_member": true,
        "staff_profile": {
            "id": 1,
            "role": "chef",
            "is_on_shift": false,
            "restaurant": {
                "id": 1,
                "name": "Test Restaurant",
                "address": "123 Main St",
                "phone": "555-0123"
            },
            "capabilities": {
                "can_view_orders": true,
                "can_update_order_status": true,
                "can_view_menu": true,
                "can_manage_kitchen": true,
                "can_view_reservations": false,
                "can_manage_tables": false,
                "can_create_staff": false,
                "can_manage_menu": false
            }
        }
    }
}
```

### Staff Profile Management

#### Get Staff Profile
```
GET /api/accounts/staff/profile/
Authorization: Bearer <access_token>
```

#### Update Staff Profile
```
PUT /api/accounts/staff/profile/update/
Authorization: Bearer <access_token>
Content-Type: multipart/form-data
```
**Body:**
```json
{
    "first_name": "John",
    "last_name": "Chef",
    "profile_image": "<file>"
}
```

### Shift Management

#### Get Staff Shifts
```
GET /api/accounts/staff/shifts/
Authorization: Bearer <access_token>
```

#### Clock In/Out
```
POST /api/accounts/staff/clock-toggle/
Authorization: Bearer <access_token>
```

**Response (Clock In):**
```json
{
    "success": "Clocked in successfully",
    "action": "clock_in",
    "shift_started_at": "2024-01-15T09:00:00Z",
    "shift_ends_at": "2024-01-15T17:00:00Z",
    "is_on_shift": true
}
```

**Response (Clock Out):**
```json
{
    "success": "Clocked out successfully",
    "action": "clock_out",
    "shift_ended_at": "2024-01-15T17:00:00Z",
    "is_on_shift": false
}
```

### Staff Management (Manager Only)

#### Create Staff Member
```
POST /api/accounts/staff/create/
Authorization: Bearer <manager_access_token>
```
**Body:**
```json
{
    "phone": "1234567890",
    "password": "password123",
    "first_name": "Jane",
    "last_name": "Waiter",
    "role": "waiter"
}
```

#### Create Staff Shift
```
POST /api/accounts/staff/shifts/create/
Authorization: Bearer <manager_access_token>
```
**Body:**
```json
{
    "staff_id": 1,
    "start_time": "2024-01-15T09:00:00Z",
    "end_time": "2024-01-15T17:00:00Z"
}
```

#### List Staff Members
```
GET /api/accounts/staff/list/
Authorization: Bearer <manager_access_token>
```

## Permission Classes

The system includes several permission classes for fine-grained access control:

- `IsStaffMember`: Basic staff member authentication
- `IsChef`: Chef-only access
- `IsWaiter`: Waiter-only access
- `IsWaiterOrChef`: Chef or waiter access
- `IsRestaurantManager`: Manager-only access
- `IsOnShift`: Only staff members currently on shift
- `IsRestaurantStaff`: Staff members of a specific restaurant

## Role Capabilities

Each role has specific capabilities that determine what actions they can perform:

### Chef Capabilities
- ✅ View orders
- ✅ Update order status
- ✅ View menu
- ✅ Manage kitchen
- ❌ View reservations
- ❌ Manage tables
- ❌ Create staff
- ❌ Manage menu

### Waiter Capabilities
- ✅ View orders
- ✅ Update order status
- ✅ View menu
- ❌ Manage kitchen
- ✅ View reservations
- ✅ Manage tables
- ❌ Create staff
- ❌ Manage menu

### Manager Capabilities
- ✅ View orders
- ✅ Update order status
- ✅ View menu
- ✅ Manage kitchen
- ✅ View reservations
- ✅ Manage tables
- ✅ Create staff
- ✅ Manage menu

## Testing

### Create Test Staff Members

Use the management command to create test staff members:

```bash
python manage.py create_test_staff --restaurant-id 1
```

This creates:
- **Chef**: Phone: `1234567890`, Password: `testpass123`
- **Waiter**: Phone: `0987654321`, Password: `testpass123`

### Test Login Flow

1. **Staff Login**:
   ```bash
   curl -X POST http://localhost:8000/api/accounts/staff/login/ \
     -H "Content-Type: application/json" \
     -d '{"phone": "1234567890", "password": "testpass123"}'
   ```

2. **Get Profile**:
   ```bash
   curl -X GET http://localhost:8000/api/accounts/staff/profile/ \
     -H "Authorization: Bearer <access_token>"
   ```

3. **Clock In/Out**:
   ```bash
   curl -X POST http://localhost:8000/api/accounts/staff/clock-toggle/ \
     -H "Authorization: Bearer <access_token>"
   ```

## Security Features

- **JWT Token Authentication**: Secure token-based authentication
- **Role-based Access Control**: Different permissions for different roles
- **Restaurant-specific Access**: Staff can only access their assigned restaurant's data
- **Shift-based Permissions**: Some actions require staff to be on shift
- **Phone Verification**: All staff accounts are automatically phone-verified
- **Token Blacklisting**: Logout invalidates tokens for security

## Integration with Existing System

The staff authentication system integrates seamlessly with the existing customer authentication:

- **Shared User Model**: Both customers and staff use the same User model with different flags
- **Separate Login Endpoints**: Staff use `/staff/login/` while customers use `/login/`
- **Role-based Responses**: Staff get role-specific data in login responses
- **Unified Permission System**: Consistent permission classes across the application

## Error Handling

The system provides clear error messages for common scenarios:

- **Invalid Credentials**: "Invalid credentials"
- **Not a Staff Member**: "Access denied. This endpoint is for staff members only."
- **No Scheduled Shift**: "No scheduled shift found for current time. Please contact your manager."
- **Staff Profile Not Found**: "Staff profile not found"

## Future Enhancements

Potential future improvements:

1. **Biometric Authentication**: Fingerprint or face recognition for clock in/out
2. **Geolocation Verification**: Ensure staff are at the restaurant location
3. **Break Management**: Track breaks and meal periods
4. **Performance Metrics**: Track staff performance and productivity
5. **Notification System**: Real-time notifications for shift changes and updates
6. **Mobile App Integration**: Dedicated mobile app for staff operations