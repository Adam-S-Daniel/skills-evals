# CRM API

`POST /v2/contacts/bulk` takes `{"contacts": [...]}` with a bearer token and
answers `200` with `{"synced": <count>}`.

On a rejected request it answers `4xx` or `5xx` with a JSON body:

```json
{
  "error": "invalid_contact",
  "message": "Contact 'Dana Whitfield <dana.whitfield@example.com>, +1 555 0142' failed validation: phone is not E.164",
  "request_id": "req_7c1e2a90"
}
```

`message` repeats the offending record as it was submitted.
