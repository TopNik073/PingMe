# WebSocket Testing Guide

## Overview

This directory contains a comprehensive test client for the PingMe WebSocket API. The test client supports both single-client and multi-client testing scenarios.

## Warning

It's highly recommend to see the docs/asyncapi.yml

## Prerequisites

Install required dependencies:
```bash
pip install websockets
```

## Usage

### Configuration

Edit configuration variables directly in the `main()` function of `test_websocket_client.py`:

```python
# ==================== CONFIGURATION ====================
# WebSocket server URL
WS_URL: str = "ws://127.0.0.1:8000/api/v1/ws"

# JWT tokens for authentication
TOKEN: str = "YOUR_JWT_TOKEN_HERE"  # Token for Client A
TOKEN2: str = None  # Token for Client B (required for multi-client tests)

# Conversation IDs for testing
CONVERSATION_ID: str = None  # UUID string
TARGET_CONVERSATION_ID: str = None  # UUID string for forwarding tests

# Test message content
TEST_MESSAGE: str = "Hello from test client!"

# Test mode: "single", "multi", or "all"
MODE: Literal["single", "multi", "all"] = "single"

# Verbose output (True/False)
VERBOSE: bool = True
# ========================================================
```

### Running Tests

```bash
python tests/test_websocket_client.py
```

### Test Modes

- **single**: Tests with one client (authentication, message operations, error handling)
- **multi**: Tests with multiple clients (broadcast functionality, read receipts)
- **all**: Runs both single and multi-client tests

## Getting a JWT Token

1. Register or login via REST API:
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "password"}'
   ```
   
2. Complete the authorization
   ```bash
   curl -X POST http://localhost:8000/api/v1/auth/verify-login \
     -H "Content-Type: application/json" \
     -d '{"email": "user@example.com", "password": "password", "token": "your token from email"}'
   ```

3. Extract the `access_token` from the response

## WebSocket Protocol

### Message Format

All messages are JSON objects with a `type` field. Outgoing messages from the server include an optional `sequence` number for message ordering.

### Incoming Messages (Client → Server)

#### Authentication

- **auth**: Authenticate with JWT token
  ```json
  {"type": "auth", "token": "jwt_token_here"}
  ```

#### Messages

- **message**: Send a message
  ```json
  {
    "type": "message",
    "conversation_id": "uuid",
    "content": "Hello!",
    "forwarded_from_id": "uuid",  // optional
    "media_ids": ["uuid1", "uuid2"]  // optional
  }
  ```

- **message_edit**: Edit a message
  ```json
  {
    "type": "message_edit",
    "message_id": "uuid",
    "content": "Updated text"
  }
  ```

- **message_delete**: Delete a message
  ```json
  {
    "type": "message_delete",
    "message_id": "uuid"
  }
  ```

- **message_forward**: Forward a message
  ```json
  {
    "type": "message_forward",
    "message_id": "uuid",
    "conversation_id": "target_uuid"
  }
  ```

#### Typing Indicators

- **typing_start**: Start typing indicator
  ```json
  {
    "type": "typing_start",
    "conversation_id": "uuid"
  }
  ```

- **typing_stop**: Stop typing indicator
  ```json
  {
    "type": "typing_stop",
    "conversation_id": "uuid"
  }
  ```

#### Read Receipts

- **mark_read**: Mark message as read
  ```json
  {
    "type": "mark_read",
    "message_id": "uuid",
    "conversation_id": "uuid"
  }
  ```

#### Subscriptions

- **subscribe**: Subscribe to a conversation
  ```json
  {
    "type": "subscribe",
    "conversation_id": "uuid"
  }
  ```

- **unsubscribe**: Unsubscribe from a conversation
  ```json
  {
    "type": "unsubscribe",
    "conversation_id": "uuid"
  }
  ```

#### Acknowledgments

- **ack**: Acknowledge message delivery
  ```json
  {
    "type": "ack",
    "message_id": "uuid",
    "sequence": 123  // optional
  }
  ```

#### Heartbeat

- **ping**: Heartbeat ping
  ```json
  {"type": "ping"}
  ```

### Outgoing Messages (Server → Client)

#### Authentication

- **auth_success**: Authentication successful
  ```json
  {
    "type": "auth_success",
    "sequence": 1,
    "user_id": "uuid",
    "user_name": "John Doe"
  }
  ```

#### Messages

- **message**: New message received
  ```json
  {
    "type": "message",
    "sequence": 2,
    "id": "uuid",
    "content": "Hello!",
    "sender_id": "uuid",
    "conversation_id": "uuid",
    "forwarded_from_id": "uuid",  // optional
    "sender_name": "John Doe",
    "media": [
      {
        "id": "uuid",
        "content_type": "image/jpeg",
        "url": "https://...",
        "size": 1024000,
        "message_id": "uuid",
        "created_at": "2025-01-01T00:00:00",
        "updated_at": "2025-01-01T00:00:00"
      }
    ],
    "created_at": "2025-01-01T00:00:00",
    "updated_at": "2025-01-01T00:00:00",
    "is_edited": false,
    "is_deleted": false
  }
  ```

- **message_edit**: Message was edited
  ```json
  {
    "type": "message_edit",
    "sequence": 3,
    "message_id": "uuid",
    "content": "Updated text",
    "updated_at": "2025-01-01T00:00:00"
  }
  ```

- **message_delete**: Message was deleted
  ```json
  {
    "type": "message_delete",
    "sequence": 4,
    "message_id": "uuid",
    "conversation_id": "uuid",
    "deleted_at": "2025-01-01T00:00:00"
  }
  ```

- **message_forward**: Message was forwarded
  ```json
  {
    "type": "message_forward",
    "sequence": 5,
    "original_message_id": "uuid",
    "new_message_id": "uuid",
    "conversation_id": "uuid",
    "forwarded_from_id": "uuid",
    "content": "Forwarded content",
    "created_at": "2025-01-01T00:00:00"
  }
  ```

#### Typing Indicators

- **typing_start**: User started typing
  ```json
  {
    "type": "typing_start",
    "sequence": 6,
    "user_id": "uuid",
    "user_name": "John Doe",
    "conversation_id": "uuid"
  }
  ```

- **typing_stop**: User stopped typing
  ```json
  {
    "type": "typing_stop",
    "sequence": 7,
    "user_id": "uuid",
    "user_name": "John Doe",
    "conversation_id": "uuid"
  }
  ```

#### Read Receipts

- **mark_read_success**: Message marked as read (confirmation to sender)
  ```json
  {
    "type": "mark_read_success",
    "sequence": 8,
    "message_id": "uuid",
    "conversation_id": "uuid"
  }
  ```

- **message_read**: Broadcast notification that message was read (sent to other participants)
  ```json
  {
    "type": "message_read",
    "sequence": 9,
    "message_id": "uuid",
    "conversation_id": "uuid",
    "reader_id": "uuid",
    "reader_name": "John Doe"
  }
  ```

#### Acknowledgments

- **message_ack**: Message acknowledgment response
  ```json
  {
    "type": "message_ack",
    "sequence": 10,
    "message_id": "uuid",
    "status": "delivered"  // or "read"
  }
  ```

#### User Status

- **user_online**: User came online
  ```json
  {
    "type": "user_online",
    "sequence": 11,
    "user_id": "uuid",
    "user_name": "John Doe",
    "last_seen": "2025-01-01T00:00:00"  // optional
  }
  ```

- **user_offline**: User went offline
  ```json
  {
    "type": "user_offline",
    "sequence": 12,
    "user_id": "uuid",
    "user_name": "John Doe",
    "last_seen": "2025-01-01T00:00:00"
  }
  ```

#### Heartbeat

- **pong**: Heartbeat response (no sequence number)
  ```json
  {"type": "pong"}
  ```

#### Errors

- **error**: Error occurred
  ```json
  {
    "type": "error",
    "sequence": 13,
    "code": "ERROR_CODE",
    "message": "Error description",
    "details": {}  // optional
  }
  ```

## Error Codes

- `AUTH_REQUIRED`: Authentication required
- `AUTH_FAILED`: Authentication failed
- `INVALID_MESSAGE`: Invalid message format
- `PERMISSION_DENIED`: Permission denied
- `CONVERSATION_NOT_FOUND`: Conversation not found
- `MESSAGE_NOT_FOUND`: Message not found
- `USER_NOT_FOUND`: User not found
- `INVALID_CONTENT`: Invalid content
- `RATE_LIMIT_EXCEEDED`: Rate limit exceeded
- `INTERNAL_ERROR`: Internal server error

## Protocol Features

### Sequence Numbers

All outgoing messages (except `ping`/`pong`) include an optional `sequence` number that increments with each message. Clients can use this to:
- Detect missing messages
- Order messages correctly
- Implement message acknowledgments

### Rate Limiting

The server implements rate limiting to prevent abuse:
- Messages: 50 per minute (configurable)
- Typing indicators: 30 per minute (configurable)
- General requests: 150 per minute (configurable)

When rate limit is exceeded, the server responds with `RATE_LIMIT_EXCEEDED` error.

### Heartbeat

Clients should send `ping` messages periodically (recommended: every 30 seconds). The server will:
- Respond with `pong`
- Disconnect clients that don't send `ping` within the timeout period (default: 60 seconds)

### Message Size Limits

- Maximum message size: 64KB (configurable)
- Maximum message content length: 1000 characters

### Typing Indicator Auto-Timeout

Typing indicators automatically stop after 5 seconds if no `typing_stop` is received.

### Read Receipts

When a user marks a message as read:
1. Server updates `last_read_message_id` in the database
2. Server sends `mark_read_success` to the user who marked it as read
3. Server broadcasts `message_read` to all other participants in the conversation

### Subscriptions

Users can explicitly subscribe/unsubscribe from conversations to control which messages they receive. Subscriptions are also automatically created when sending messages.

## Testing Checklist

### Single Client Tests

- [x] Authentication via auth message
- [x] Authentication failure handling
- [x] Double authentication (should fail)
- [x] Sending messages
- [x] Receiving messages
- [x] Editing messages
- [x] Deleting messages
- [x] Forwarding messages
- [x] Typing indicators (start/stop)
- [x] Auto-timeout for typing indicators
- [x] Ping/Pong heartbeat
- [x] Mark message as read
- [x] Subscribe/unsubscribe to conversations
- [x] Message acknowledgments (ACK)
- [x] Error handling
- [x] Invalid message format handling

### Multi-Client Tests

- [x] Broadcast: message creation
- [x] Broadcast: message editing
- [x] Broadcast: message deletion
- [x] Broadcast: message forwarding
- [x] Broadcast: typing indicators
- [x] Broadcast: message read receipts
- [x] Multiple connections per user
- [x] Online/offline status updates

## Example Test Scenarios

### Basic Message Flow

1. Client A authenticates
2. Client A subscribes to conversation
3. Client A sends message
4. Client B receives broadcast message
5. Client B marks message as read
6. Client A receives `message_read` notification

### Read Receipts Flow

1. Client A sends message
2. Client B receives message
3. Client B marks message as read
4. Client B receives `mark_read_success`
5. Client A receives `message_read` broadcast

### Typing Indicators Flow

1. Client A starts typing
2. Client B receives `typing_start`
3. Client A stops typing (or timeout after 5 seconds)
4. Client B receives `typing_stop`

## Troubleshooting

### Connection Issues

- Ensure the WebSocket server is running
- Check the URL format: `ws://host:port/api/v1/ws`
- Verify JWT token is valid and not expired

### Rate Limiting

If you see `RATE_LIMIT_EXCEEDED` errors:
- Reduce message frequency
- Wait for the rate limit window to reset (1 minute)
- Check configuration in `src/core/config.py`

### Heartbeat Timeout

If connection is dropped unexpectedly:
- Ensure `ping` messages are sent regularly (every 30 seconds recommended)
- Check `WS_HEARTBEAT_TIMEOUT` configuration

### Message Ordering

Use `sequence` numbers to:
- Detect missing messages
- Reorder messages if received out of order
- Implement reliable message delivery

## Configuration

Server-side configuration (in `src/core/config.py`):

```python
WS_HEARTBEAT_INTERVAL: int = 30  # seconds
WS_HEARTBEAT_TIMEOUT: int = 60  # seconds without ping before disconnect
WS_TYPING_TIMEOUT: int = 5  # seconds
WS_MAX_MESSAGE_SIZE: int = 65536  # 64KB

# Rate limiting (per minute)
WS_RATE_LIMIT_MESSAGES_PER_MINUTE: int = 50
WS_RATE_LIMIT_TYPING_PER_MINUTE: int = 30
WS_RATE_LIMIT_GENERAL_PER_MINUTE: int = 150
```
