# Session Management API Documentation

This document provides comprehensive documentation for the prompt-to-IR session management API in lift-sys.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Endpoints](#endpoints)
  - [Create Session](#create-session)
  - [List Sessions](#list-sessions)
  - [Get Session](#get-session)
  - [Resolve Hole](#resolve-hole)
  - [Finalize Session](#finalize-session)
  - [Get Assists](#get-assists)
  - [Delete Session](#delete-session)
- [Data Models](#data-models)
- [Usage Examples](#usage-examples)
- [Error Handling](#error-handling)

## Overview

The session management API enables iterative refinement of natural language prompts into validated Intermediate Representation (IR). The workflow consists of:

1. **Create** a session from a natural language prompt or existing IR
2. **Resolve** ambiguities (typed holes) identified by the translator
3. **Get assists** for suggestions on how to resolve holes
4. **Finalize** the session once all holes are resolved
5. **Delete** sessions when no longer needed

All endpoints require authentication and emit WebSocket events for real-time UI updates.

## Authentication

All session management endpoints require OAuth authentication. Include credentials in your requests:

**Web/Frontend:**
```typescript
// Using axios with credentials
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  withCredentials: true,
});
```

**Python SDK:**
```python
from lift_sys.client import SessionClient

# Will use session cookies automatically
client = SessionClient('http://localhost:8000')
```

**CLI:**
```bash
# Authentication handled automatically via session
uv run python -m lift_sys.cli session list
```

**cURL:**
```bash
# Include session cookie
curl -X GET http://localhost:8000/spec-sessions \
  -H "Cookie: session=YOUR_SESSION_COOKIE"

# Or use demo user header (development only)
export LIFT_SYS_ENABLE_DEMO_USER_HEADER=1
curl -X GET http://localhost:8000/spec-sessions \
  -H "x-demo-user: testuser"
```

## Endpoints

### Create Session

Create a new prompt refinement session from a natural language prompt or existing IR.

**Endpoint:** `POST /spec-sessions`

**Request Body:**
```json
{
  "prompt": "A function that takes two integers and returns their sum",
  "source": "prompt",
  "metadata": {
    "user_notes": "Simple addition function"
  }
}
```

Or from IR:
```json
{
  "ir": {
    "intent": {
      "summary": "Add two numbers"
    },
    "signature": {
      "name": "add",
      "parameters": [],
      "returns": "int"
    }
  },
  "source": "reverse_mode"
}
```

**Response:** `200 OK`
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "source": "prompt",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z",
  "current_draft": {
    "version": 1,
    "ir": {
      "intent": {
        "summary": "Add two numbers"
      },
      "signature": {
        "name": "<?hole_function_name: str>",
        "parameters": [
          {"name": "<?hole_param1_name: str>", "type_hint": "<?hole_param1_type: str>"},
          {"name": "<?hole_param2_name: str>", "type_hint": "<?hole_param2_type: str>"}
        ],
        "returns": "<?hole_return_type: str>"
      },
      "effects": [],
      "assertions": []
    },
    "validation_status": "incomplete",
    "ambiguities": ["hole_function_name", "hole_param1_name", "hole_param1_type", "hole_param2_name", "hole_param2_type", "hole_return_type"],
    "smt_results": [],
    "created_at": "2025-01-15T10:30:00Z",
    "metadata": {}
  },
  "ambiguities": ["hole_function_name", "hole_param1_name", "hole_param1_type", "hole_param2_name", "hole_param2_type", "hole_return_type"],
  "revision_count": 1,
  "metadata": {
    "user_notes": "Simple addition function"
  }
}
```

**WebSocket Event:**
```json
{
  "type": "session_created",
  "scope": "spec_sessions",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "ambiguities": 6
}
```

### List Sessions

List all active sessions for the authenticated user.

**Endpoint:** `GET /spec-sessions`

**Response:** `200 OK`
```json
{
  "sessions": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "status": "active",
      "source": "prompt",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:35:00Z",
      "current_draft": { /* ... */ },
      "ambiguities": ["hole_return_type"],
      "revision_count": 5,
      "metadata": {}
    }
  ]
}
```

### Get Session

Get detailed information about a specific session.

**Endpoint:** `GET /spec-sessions/{session_id}`

**Response:** `200 OK`
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "source": "prompt",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:35:00Z",
  "current_draft": {
    "version": 5,
    "ir": { /* complete IR */ },
    "validation_status": "incomplete",
    "ambiguities": ["hole_return_type"],
    "smt_results": [],
    "created_at": "2025-01-15T10:35:00Z",
    "metadata": {}
  },
  "ambiguities": ["hole_return_type"],
  "revision_count": 5,
  "metadata": {}
}
```

**Error:** `404 Not Found`
```json
{
  "detail": "Session not found"
}
```

### Resolve Hole

Resolve a typed hole in a session, updating the IR draft.

**Endpoint:** `POST /spec-sessions/{session_id}/holes/{hole_id}/resolve`

**Request Body:**
```json
{
  "resolution_text": "int",
  "resolution_type": "clarify_intent"
}
```

**Response:** `200 OK`
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "active",
  "source": "prompt",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:36:00Z",
  "current_draft": {
    "version": 6,
    "ir": {
      "signature": {
        "returns": "int"  // Hole resolved
      }
    },
    "validation_status": "valid",
    "ambiguities": [],
    "smt_results": [],
    "created_at": "2025-01-15T10:36:00Z",
    "metadata": {}
  },
  "ambiguities": [],
  "revision_count": 6,
  "metadata": {}
}
```

**WebSocket Event:**
```json
{
  "type": "hole_resolved",
  "scope": "spec_sessions",
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "hole_id": "hole_return_type",
  "remaining_holes": 0
}
```

### Finalize Session

Finalize a session and return the completed IR. Session must have no unresolved holes.

**Endpoint:** `POST /spec-sessions/{session_id}/finalize`

**Response:** `200 OK`
```json
{
  "ir": {
    "intent": {
      "summary": "Add two numbers",
      "rationale": null
    },
    "signature": {
      "name": "add",
      "parameters": [
        {"name": "a", "type_hint": "int"},
        {"name": "b", "type_hint": "int"}
      ],
      "returns": "int"
    },
    "effects": [],
    "assertions": [
      {
        "predicate": "result == a + b",
        "rationale": "Output equals sum of inputs"
      }
    ]
  },
  "metadata": {
    "finalized_at": "2025-01-15T10:40:00Z",
    "total_revisions": 6
  }
}
```

**Error:** `400 Bad Request`
```json
{
  "detail": "Cannot finalize session with unresolved holes"
}
```

### Get Assists

Get actionable suggestions for resolving holes in a session.

**Endpoint:** `GET /spec-sessions/{session_id}/assists`

**Response:** `200 OK`
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "assists": [
    {
      "hole_id": "hole_return_type",
      "suggestions": ["int", "float", "number"],
      "context": "Return type for addition operation. Based on input types, likely numeric."
    },
    {
      "hole_id": "hole_param1_type",
      "suggestions": ["int", "float"],
      "context": "Type annotation for first parameter in addition function."
    }
  ]
}
```

### Delete Session

Delete a session and all associated data.

**Endpoint:** `DELETE /spec-sessions/{session_id}`

**Response:** `200 OK`
```json
{
  "message": "Session deleted successfully"
}
```

## Data Models

### PromptSession

```typescript
interface PromptSession {
  session_id: string;
  status: "active" | "finalized" | "abandoned";
  source: "prompt" | "reverse_mode";
  created_at: string;  // ISO 8601
  updated_at: string;  // ISO 8601
  current_draft: IRDraft | null;
  ambiguities: string[];  // List of hole IDs
  revision_count: number;
  metadata: Record<string, any>;
}
```

### IRDraft

```typescript
interface IRDraft {
  version: number;
  ir: IntermediateRepresentation;
  validation_status: "pending" | "incomplete" | "valid" | "contradictory";
  ambiguities: string[];
  smt_results: Array<Record<string, any>>;
  created_at: string;
  metadata: Record<string, any>;
}
```

### IntermediateRepresentation

```typescript
interface IntermediateRepresentation {
  intent: {
    summary: string;
    rationale?: string | null;
  };
  signature: {
    name: string;
    parameters: Array<{ name: string; type_hint: string }>;
    returns?: string | null;
  };
  effects: Array<{ description: string }>;
  assertions: Array<{
    predicate: string;
    rationale?: string | null;
  }>;
}
```

## Usage Examples

### Complete Workflow (Python SDK)

```python
from lift_sys.client import SessionClient

# Initialize client
client = SessionClient('http://localhost:8000')

# 1. Create session
session = client.create_session(
    prompt="A function that validates email addresses"
)
print(f"Created session: {session.session_id}")
print(f"Holes to resolve: {len(session.ambiguities)}")

# 2. Get suggestions
assists = client.get_assists(session.session_id)
for assist in assists.assists:
    print(f"Hole: {assist.hole_id}")
    print(f"Context: {assist.context}")
    print(f"Suggestions: {', '.join(assist.suggestions)}")

# 3. Resolve holes
for hole_id in session.ambiguities[:3]:
    session = client.resolve_hole(
        session_id=session.session_id,
        hole_id=hole_id,
        resolution_text="str"  # Example resolution
    )
    print(f"Resolved {hole_id}, {len(session.ambiguities)} remaining")

# 4. Finalize when ready
if len(session.ambiguities) == 0:
    ir_response = client.finalize_session(session.session_id)
    print("Session finalized!")
    print(f"IR: {ir_response.ir}")
```

### Complete Workflow (TypeScript/Frontend)

```typescript
import {
  createSession,
  getAssists,
  resolveHole,
  finalizeSession,
} from './lib/sessionApi';

// 1. Create session
const session = await createSession({
  prompt: 'A function that validates email addresses',
});

console.log(`Created: ${session.session_id}`);
console.log(`Holes: ${session.ambiguities.length}`);

// 2. Get suggestions
const assists = await getAssists(session.session_id);
for (const assist of assists.assists) {
  console.log(`${assist.hole_id}: ${assist.suggestions.join(', ')}`);
}

// 3. Resolve holes
for (const holeId of session.ambiguities) {
  const updated = await resolveHole(session.session_id, holeId, {
    resolution_text: 'str',
    resolution_type: 'clarify_intent',
  });
  console.log(`Resolved ${holeId}, ${updated.ambiguities.length} remaining`);
}

// 4. Finalize
const result = await finalizeSession(session.session_id);
console.log('Finalized:', result.ir);
```

### Complete Workflow (CLI)

```bash
# 1. Create session
SESSION_ID=$(uv run python -m lift_sys.cli session create \
  -p "A function that validates email addresses" \
  --json | jq -r '.session_id')

echo "Created session: $SESSION_ID"

# 2. Get suggestions
uv run python -m lift_sys.cli session assists $SESSION_ID

# 3. List holes
uv run python -m lift_sys.cli session get $SESSION_ID

# 4. Resolve holes
uv run python -m lift_sys.cli session resolve $SESSION_ID hole_function_name "validate_email"
uv run python -m lift_sys.cli session resolve $SESSION_ID hole_return_type "bool"

# 5. Finalize
uv run python -m lift_sys.cli session finalize $SESSION_ID -o email_validator.json

echo "IR saved to email_validator.json"
```

### Complete Workflow (cURL)

```bash
# 1. Create session
SESSION_ID=$(curl -X POST http://localhost:8000/spec-sessions \
  -H "Content-Type: application/json" \
  -H "x-demo-user: testuser" \
  -d '{"prompt": "A function that validates email addresses"}' \
  | jq -r '.session_id')

echo "Created: $SESSION_ID"

# 2. Get session details
curl http://localhost:8000/spec-sessions/$SESSION_ID \
  -H "x-demo-user: testuser" | jq .

# 3. Resolve hole
curl -X POST http://localhost:8000/spec-sessions/$SESSION_ID/holes/hole_return_type/resolve \
  -H "Content-Type: application/json" \
  -H "x-demo-user: testuser" \
  -d '{"resolution_text": "bool", "resolution_type": "clarify_intent"}' \
  | jq .

# 4. Finalize
curl -X POST http://localhost:8000/spec-sessions/$SESSION_ID/finalize \
  -H "x-demo-user: testuser" \
  | jq . > email_validator.json
```

## Error Handling

### Common Error Codes

| Status Code | Description | Example |
|-------------|-------------|---------|
| 400 | Bad Request | Missing required fields, invalid data |
| 401 | Unauthorized | Missing or invalid authentication |
| 404 | Not Found | Session ID does not exist |
| 422 | Unprocessable Entity | Invalid request body schema |
| 500 | Internal Server Error | Server-side error |

### Error Response Format

```json
{
  "detail": "Error message describing what went wrong"
}
```

### Python SDK Error Handling

```python
import httpx
from lift_sys.client import SessionClient

client = SessionClient('http://localhost:8000')

try:
    session = client.create_session(prompt="Test")
except httpx.HTTPStatusError as e:
    if e.response.status_code == 401:
        print("Authentication required")
    elif e.response.status_code == 404:
        print("Session not found")
    else:
        print(f"Error: {e.response.json()['detail']}")
except httpx.RequestError as e:
    print(f"Connection error: {e}")
```

### Frontend Error Handling

```typescript
import { createSession } from './lib/sessionApi';

try {
  const session = await createSession({ prompt: 'Test' });
} catch (error) {
  if (error.response?.status === 401) {
    console.error('Authentication required');
  } else if (error.response?.status === 404) {
    console.error('Session not found');
  } else {
    console.error('Error:', error.response?.data?.detail);
  }
}
```

## WebSocket Events

Subscribe to `/ws/progress` for real-time updates. Filter by `scope: "spec_sessions"`:

```typescript
const ws = new WebSocket('ws://localhost:8000/ws/progress');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.scope === 'spec_sessions') {
    switch (data.type) {
      case 'session_created':
        console.log(`New session: ${data.session_id}`);
        break;
      case 'hole_resolved':
        console.log(`Hole resolved: ${data.hole_id}`);
        break;
      case 'session_finalized':
        console.log(`Session finalized: ${data.session_id}`);
        break;
    }
  }
};
```

## Rate Limiting

API requests are rate-limited per user:
- **Default**: 60 requests per 60 seconds
- Rate limit headers included in responses:
  ```
  X-RateLimit-Limit: 60
  X-RateLimit-Remaining: 59
  X-RateLimit-Reset: 1642248000
  ```

## Best Practices

1. **Check for ambiguities** after creating a session
2. **Use assists API** to get context-aware suggestions
3. **Validate progressively** by resolving one hole at a time
4. **Subscribe to WebSocket** for real-time updates in UIs
5. **Save IR** after finalization for code generation
6. **Clean up** by deleting sessions when done
7. **Use JSON output** in CLI for automation scripts
8. **Handle errors gracefully** with appropriate retry logic

## Support

For issues or questions:
- GitHub Issues: https://github.com/rand/lift-sys/issues
- Documentation: https://github.com/rand/lift-sys/tree/main/docs
- API Reference: http://localhost:8000/docs (when running locally)
