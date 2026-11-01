# API specification

The JSON API that the warehouse robots use. Browsers use the HTML pages instead (see [Robot communication](architecture.md#robot-communication) in the software architecture).

## Contents

1. [General agreements](#general-agreements)
2. [Errors](#errors)
3. [GET /api/health](#get-apihealth)
4. [POST /api/picking-bins](#post-apipicking-bins)
5. [Planned endpoints](#planned-endpoints)

## General agreements

- Base path: `/api`. All routes are in `code/backend/routes/api.py`.
- Requests and answers are JSON (`Content-Type: application/json`). Field names are English and match the domain classes.
- Calls that change data are `POST`. The robot sends its aisle (`"A"` to `"H"`) in every call that changes data.
- Every answer has an HTTP status code that matches the result:

| Status | Meaning |
| --- | --- |
| 200 | Success |
| 400 | Wrong request: missing or invalid field, or a broken business rule |
| 404 | Unknown object, for example an unknown sub-order, or an unknown route |
| 405 | The route exists, but not for this HTTP method |
| 409 | Conflict with the current state, for example a bin code that is already registered |
| 500 | Unexpected error in the backend |
| 503 | The database cannot be reached |

- Several robots work on one order at the same time. Calls that change data run in one database transaction, and the transaction decides the final state.

## Errors

Every answer with a status of 400 or higher has the same body. The error handlers in `code/backend/app.py` build it.

```json
{"error": "Deelorder 7 bestaat niet."}
```

`error` is a readable message. Messages for broken business rules are Dutch, because they come from the services. Messages for 404/405 routes, 500 and 503 are English.

## GET /api/health

Tells a robot whether the backend and the database are up. It changes nothing.

**Request:** no body.

**Response 200:**

```json
{"status": "ok", "database": true}
```

| Field | Type | Description |
| --- | --- | --- |
| `status` | string | Always `"ok"` when the backend answers |
| `database` | boolean | `true` when the database answered a test query |

**Errors:**

| Status | When |
| --- | --- |
| 503 | The database cannot be reached. Body: `{"error": "The database cannot be reached. Try again later."}` |

## POST /api/picking-bins

A robot scanned the unique code of a picking bin (`Verzamelbak`) and links it to the sub-order (`Deelorder`) it is collecting. Issue #17, activity diagram AD10.

**Request:**

```json
{"aisle": "B", "sub_order_id": 7, "bin_code": "VB-0001"}
```

| Field | Type | Required | Rule |
| --- | --- | --- | --- |
| `aisle` | string | yes | `"A"` to `"H"`, case-insensitive. Must be the aisle of the robot assigned to the sub-order. A number is rejected. |
| `sub_order_id` | integer | yes | A positive whole number. A string with digits, such as `"7"`, is accepted too. |
| `bin_code` | string | yes | 1 to 50 characters: letters, digits, `-` or `_`. Spaces around it are removed. A number is rejected, so send `"123"`, not `123`. |

**Response 200:**

```json
{"accepted": true, "bin_code": "VB-0001", "order_id": 3, "sub_order_id": 7, "aisle": "B"}
```

| Field | Type | Description |
| --- | --- | --- |
| `accepted` | boolean | Always `true` on 200 |
| `bin_code` | string | The registered bin code |
| `order_id` | integer | The order (`Bestelling`) the sub-order belongs to |
| `sub_order_id` | integer | The sub-order the bin is linked to |
| `aisle` | string | The aisle of the robot, in capitals |

**Errors**, in the order the backend checks them:

| Status | When | Example `error` |
| --- | --- | --- |
| 400 | The body is not a JSON object | `Stuur een JSON-object met aisle, sub_order_id en bin_code.` |
| 400 | `bin_code` is missing or has the wrong format | `Vul een bakcode in van maximaal 50 tekens met alleen letters, cijfers, - of _.` |
| 400 | `sub_order_id` is missing or not a positive whole number | `Het deelordernummer moet een positief geheel getal zijn.` |
| 400 | `aisle` is missing or not A to H | `Kies een gang van A tot en met H.` |
| 404 | The sub-order does not exist | `Deelorder 7 bestaat niet.` |
| 409 | The sub-order is already completed | `Deelorder 7 is al afgerond. Koppel de bak aan een open deelorder.` |
| 400 | The sub-order is collected in another aisle | `Deelorder 7 wordt verzameld in gang B, niet in gang C.` |
| 409 | The bin code is already registered, also when two robots send it at the same time | `Verzamelbak VB-0001 is al geregistreerd bij deelorder 5.` |

The first three checks run before any query. The rest run in one transaction that locks the sub-order, so nothing is stored when a check fails.

**What is stored:** one row in `Verzamelbak` (`unieke_code`, `deelorder_id`). The query is in `PickingBinRepository.register()` and in `code/database/queries.sql`. The `/order-picking` page reads the same data to show which order is in which bins.

## Planned endpoints

These calls follow from [Robot communication](architecture.md#robot-communication) and the order picking activity diagram. They are not built or specified yet:

- Get the next partial order for this aisle.
- Report that a bin is full and on the conveyor belt.
- Report that the partial order is complete, so a new one can be assigned.

Add each one to this document in the same format when it is built.
