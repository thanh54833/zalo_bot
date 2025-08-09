# Zalo API Integration Documentation

This document describes the Zalo API integration endpoints using the unofficial zlapi library.

## Authentication

### Login
- **Endpoint:** `/api/zalo/login`
- **Method:** POST
- **Body:**
  ```json
  {
    "username": "your_zalo_phone_number",
    "password": "your_zalo_password"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "message": "Login successful",
    "data": {
      "username": "your_zalo_phone_number"
    }
  }
  ```

### Logout
- **Endpoint:** `/api/zalo/logout`
- **Method:** POST
- **Body:**
  ```json
  {
    "username": "your_zalo_phone_number"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "message": "Logout successful",
    "data": null
  }
  ```

## Messaging

### Send Message
- **Endpoint:** `/api/zalo/send-message`
- **Method:** POST
- **Body:**
  ```json
  {
    "username": "your_zalo_phone_number",
    "recipient_id": "recipient_id",
    "message": "Hello, this is a test message",
    "thread_type": "USER",
    "style": {
      "offset": 0,
      "length": 5,
      "style": "bold",
      "color": "ff0000",
      "size": "18"
    },
    "mentions": [
      {
        "uid": "user_id_to_mention",
        "length": 5,
        "offset": 0
      }
    ]
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "message": "Message sent successfully",
    "data": null
  }
  ```

## Conversations

### Get Conversations
- **Endpoint:** `/api/zalo/conversations`
- **Method:** GET
- **Query Parameters:**
  - `username`: Your Zalo phone number
- **Response:**
  ```json
  {
    "success": true,
    "message": "Conversations retrieved successfully",
    "data": {
      "conversations": [...]
    }
  }
  ```

### Get Messages
- **Endpoint:** `/api/zalo/messages/{thread_id}`
- **Method:** GET
- **Query Parameters:**
  - `username`: Your Zalo phone number
- **Response:**
  ```json
  {
    "success": true,
    "message": "Messages retrieved successfully",
    "data": {
      "messages": [...]
    }
  }
  ```

## Message Actions

### Mark as Read
- **Endpoint:** `/api/zalo/mark-as-read`
- **Method:** POST
- **Body:**
  ```json
  {
    "username": "your_zalo_phone_number",
    "thread_id": "thread_id",
    "message_id": "message_id",
    "client_message_id": "client_message_id",
    "sender_id": "sender_id",
    "thread_type": "USER"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "message": "Message marked as read",
    "data": null
  }
  ```

## Event Listening

### Start Listening
- **Endpoint:** `/api/zalo/start-listening`
- **Method:** POST
- **Body:**
  ```json
  {
    "username": "your_zalo_phone_number",
    "webhook_url": "https://your-webhook-url.com/webhook"
  }
  ```
- **Response:**
  ```json
  {
    "success": true,
    "message": "Started listening for events",
    "data": null
  }
  ```

## Webhook Events

When events are received, they will be forwarded to the webhook URL provided in the start-listening endpoint.

### Message Event
```json
{
  "event_type": "message",
  "data": {
    "message_id": "message_id",
    "author_id": "author_id",
    "message": "message_content",
    "thread_id": "thread_id",
    "thread_type": "USER"
  }
}
```

### Other Events
```json
{
  "event_type": "event",
  "data": {
    "event_data": {...},
    "event_type": "EVENT_TYPE"
  }
}
``` 