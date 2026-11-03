# Worker boundary

Phase 2 runs real Redis/RQ PDF ingestion using JSON-serialized UUID job payloads.
`python -m app.workers.run` starts the consumer. Native parsing runs in a bounded
subprocess. Application job records are authoritative for processing success;
an RQ function finishing normally can still represent a recorded business failure.
No meeting, email or presentation workers run in this phase.
