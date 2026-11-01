# API specification

The JSON API that the warehouse robots use. Browsers use the HTML pages instead (see [Robot communication](architecture.md#robot-communication) in the software architecture).

## Contents

1. [General agreements](#general-agreements)
2. [Errors](#errors)
3. [POST /api/picking-bins](#post-apipicking-bins)
4. [GET /api/robots/{robot_id}/next](#get-apirobotsrobot_idnext)
5. [POST /api/robots/{robot_id}/complete](#post-apirobotsrobot_idcomplete)
6. [POST /api/orders/{order_id}/suborders](#post-apiordersorder_idsuborders)

## General agreements

- Base path: `/api`. All routes are in `code/backend/routes/api.py`.
- Requests and answers are JSON (`Content-Type: application/json`). Field names are English and match the domain classes.
- Calls that change data are `POST`. Robot calls that change a sub-order include its aisle (`"A"` to `"H"`).
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

## GET /api/robots/{robot_id}/next

Returns the next unfinished sub-order assigned to the robot and its product lines.

**Request:** no body. The `aisle` query parameter is required.

```http
GET /api/robots/1/next?aisle=A
```

**Response 200, when a sub-order is available:**

```json
{"suborder": {"deelorder_id": 7, "bestelling_id": 3}, "lines": [{"product_id": 4, "productnaam": "Medicijn", "aantal": 2, "magazijnlocaties": "A4, A8"}]}
```

When no sub-order is available, `suborder` is `null` and `lines` is an empty array.

**Errors:** 400 for a missing or invalid aisle; 404 when the robot is not assigned to that aisle.

## POST /api/robots/{robot_id}/complete

Marks an unfinished sub-order complete after a picking bin has been registered. The robot must explicitly report the actual collected quantity for **every** assigned product, including zero when a product could not be collected.

**Request:**

```json
{"aisle": "A", "suborder_id": 7, "collected": [{"product_id": 4, "quantity": 1}]}
```

**Response 200:**

```json
{"deelorder_id": 7, "afgerond": true, "backorder": true}
```

**Effects:** Physical stock is reduced only by the confirmed collected quantity. The original ordered amount is kept in `Bestelregel.aantal`. `Deelorderregel.aantal` records the actual collected amount after completion; uncollected zero-quantity lines are omitted because the database allows only positive line quantities. Stock reservations for this completed sub-order are released. If less was collected than assigned, the order is marked as backorder; only collected medicines can be packaged and invoiced.

**Errors:** 400 for a non-object body, invalid aisle/identifier, missing collected quantities, duplicate products or invalid counts; 404 when the robot is not assigned to the aisle or the sub-order does not belong to it; 409 when the sub-order is already complete, has no lines, has no registered bin, or the reported quantities are inconsistent with the assignment or physical stock.

## POST /api/orders/{order_id}/suborders

Splits an order's reserved quantities across robot aisles. The order-picking screen exposes this action to an employee; the API supports the same operation for integrations.

**Request:** no body.

**Response 201:**

```json
{"suborders": [{"robot_id": 1, "suborder_id": 40, "lines": [{"product_id": 4, "aantal": 2}]}]}
```

**Errors:** 400 for an invalid order identifier; 404 when the order or a reserved product does not exist; 409 when the order is not ready, its sub-orders already exist, or available warehouse stock cannot fulfill its reservations.
