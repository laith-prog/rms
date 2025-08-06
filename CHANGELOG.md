# Changelog

## [Latest] - 2025-08-06

### Added

#### Staff Authentication System
- **Comprehensive Role-Based Authentication**: Implemented a sophisticated authentication system for restaurant staff with distinct roles and permissions
  - Created detailed documentation in `STAFF_AUTH_README.md` with API specifications, permission classes, and testing instructions
  - Developed four distinct staff roles (Chef, Waiter, Manager, Employee) with specific capabilities for each
  - Implemented JWT token-based authentication with role-specific claims and payload data
  - Added support for restaurant-specific staff assignments to prevent cross-restaurant access

#### Shift Management System
- **Staff Shift Tracking**: Built a complete shift management system for restaurant operations
  - Implemented clock in/out functionality with timestamp recording
  - Added shift scheduling capabilities for managers to assign staff working hours
  - Created shift validation to ensure staff can only perform certain actions while on active shifts
  - Added `is_on_shift` flag to staff profiles for real-time status tracking

#### Staff Management Tools
- **Management Command**: Created `create_test_staff.py` management command for development and testing
  - Generates test chef account with kitchen management capabilities
  - Creates test waiter account with table and reservation management capabilities
  - Automatically assigns staff to a specified restaurant based on command-line argument
  - Sets up pre-configured test credentials for immediate API testing

#### Restaurant Operational Enhancements
- **Multi-Floor Support**: Added comprehensive floor management for multi-level restaurants
  - Implemented floor designation for tables with six predefined options (Ground Floor through Rooftop)
  - Created floor-based table organization for better space management
  - Added floor filtering capabilities for table availability searches

- **Reservation Duration Tracking**: Enhanced reservation system with time management
  - Added `duration_hours` field to track how long each reservation will last
  - Implemented validation to ensure minimum 1-hour reservation duration
  - Added conflict detection to prevent double-booking tables based on duration overlap

### Modified

#### Account System Enhancements
- **Permission System Overhaul**: Completely redesigned the permission system to support fine-grained access control
  - Added seven new permission classes for role-based authorization:
    - `IsStaffMember`: Basic staff authentication
    - `IsChef`: Chef-specific permissions
    - `IsWaiter`: Waiter-specific permissions
    - `IsWaiterOrChef`: Combined role permissions
    - `IsRestaurantManager`: Manager-only capabilities
    - `IsOnShift`: Shift-based permission validation
    - `IsRestaurantStaff`: Restaurant-specific access control
  
- **Serializer Enhancements**: Extended serializers to support staff-specific data
  - Added staff profile data to user serializers with role information
  - Implemented capability-based serialization to show available actions based on role
  - Added restaurant information to staff profile serialization

- **View and URL Updates**: Expanded the API surface to support staff operations
  - Added 8 new staff-specific endpoints to the URL configuration
  - Updated views to implement role-based access control
  - Added specialized view logic for different staff roles

#### Restaurant System Modifications
- **Reservation System Updates**: Enhanced the reservation system for better management
  - Modified reservation creation to require duration specification
  - Updated reservation validation to check for conflicts based on duration
  - Added staff-specific reservation management capabilities

- **Table Management Improvements**: Redesigned table management for multi-floor support
  - Updated table uniqueness constraints to include floor designation
  - Modified table availability checks to consider floor information
  - Enhanced table assignment logic for reservations

- **View Permission Integration**: Updated views to respect staff role capabilities
  - Added permission checks based on staff role for all restaurant operations
  - Implemented shift-based permission validation for critical operations
  - Added restaurant-specific filtering to prevent cross-restaurant access

### Database Changes

#### Schema Updates
- **Reservation Model**: Enhanced with duration tracking
  - Added `duration_hours` field (IntegerField, default: 1)
  - Added help text: "Duration in hours (minimum 1 hour)"
  - Required field for all new reservations

- **Table Model**: Updated with floor designation
  - Added `floor` field (CharField, max_length: 20)
  - Implemented choices with six options:
    - 'ground': 'Ground Floor'
    - 'first': 'First Floor'
    - 'second': 'Second Floor'
    - 'third': 'Third Floor'
    - 'fourth': 'Fourth Floor'
    - 'rooftop': 'Rooftop'
  - Default value: 'ground'

- **Uniqueness Constraints**: Modified table uniqueness
  - Updated unique_together to include ('restaurant', 'table_number', 'floor')
  - Allows same table number on different floors

### API Endpoints

#### Staff Authentication Endpoints
- **`/api/accounts/staff/login/`**: Staff-specific login endpoint
  - Accepts phone and password credentials
  - Returns JWT tokens with staff-specific payload
  - Includes staff profile with role and restaurant information
  - Returns capability object showing available actions

#### Staff Profile Management
- **`/api/accounts/staff/profile/`**: Get current staff profile
  - Returns detailed staff information including role and restaurant
  - Includes current shift status and capabilities

- **`/api/accounts/staff/profile/update/`**: Update staff profile
  - Allows updating personal information
  - Supports profile image upload
  - Maintains role and restaurant assignments

#### Shift Management Endpoints
- **`/api/accounts/staff/shifts/`**: Get staff shift information
  - Returns past, current, and upcoming shifts
  - Shows shift duration and status

- **`/api/accounts/staff/clock-toggle/`**: Clock in/out functionality
  - Toggles current shift status
  - Records timestamp for shift start/end
  - Validates against scheduled shifts

#### Manager-Only Endpoints
- **`/api/accounts/staff/create/`**: Create new staff members
  - Manager-only endpoint
  - Creates staff user with specified role
  - Assigns to manager's restaurant

- **`/api/accounts/staff/shifts/create/`**: Create staff shifts
  - Allows scheduling future shifts
  - Sets shift duration and assignment

- **`/api/accounts/staff/list/`**: List all staff members
  - Shows all staff for manager's restaurant
  - Includes role and status information

### Testing

#### Test Data Generation
- Added comprehensive management command for generating test data
  - Creates chef and waiter test accounts
  - Sets up predefined credentials for testing
  - Assigns staff to specified restaurant

#### API Testing Instructions
- Provided detailed testing instructions in STAFF_AUTH_README.md
  - Added step-by-step testing workflow
  - Included sample curl commands for all endpoints
  - Documented expected responses and error cases

#### Test User Credentials
- Created default test accounts for immediate testing:
  - Chef: Phone: 1234567890, Password: testpass123
  - Waiter: Phone: 0987654321, Password: testpass123

### Security

#### Authentication Enhancements
- **JWT Token Improvements**: Enhanced JWT token security
  - Added role-specific claims to tokens
  - Implemented token versioning for invalidation
  - Added restaurant ID to token payload for validation

#### Access Control
- **Fine-Grained Permissions**: Implemented detailed permission system
  - Added role-based permission classes
  - Implemented capability-based authorization
  - Created shift-based access control

#### Data Isolation
- **Restaurant-Specific Access**: Ensured data isolation between restaurants
  - Staff can only access their assigned restaurant's data
  - Managers can only manage staff within their restaurant
  - Implemented restaurant ID validation on all endpoints

#### Integration
- **Unified Authentication**: Seamlessly integrated with existing system
  - Works alongside customer authentication
  - Uses same User model with role flags
  - Maintains consistent security patterns