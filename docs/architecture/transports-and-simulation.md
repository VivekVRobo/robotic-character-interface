# Transports and Simulation

PR-007 establishes the byte-stream boundary used by future serial/radio adapters and software-in-the-loop simulation.

## Layers

```text
protocol Frame
  -> ProtocolTransport
  -> AsyncByteTransport
  -> MemoryByteTransport (simulation now)
  -> SerialTransport / physical adapters (future)
```

`AsyncByteTransport` is intentionally byte-oriented. Packet framing, CRC validation, resynchronization, and protocol semantics remain in the protocol layer rather than being hidden inside hardware drivers.

## Bounded memory transport

`MemoryByteTransport` is a full-duplex, bounded, one-shot transport pair. Writes apply backpressure when the peer buffer is full. A single write larger than the configured channel capacity is rejected. Remote close produces EOF for readers and rejects later writes.

The implementation is deterministic and contains no random latency, corruption, or packet loss. Faults are injected explicitly by tests so failures are reproducible.

## Stream decoder

`FrameStreamDecoder` accepts arbitrary byte chunks and can reconstruct frames delivered one byte at a time or many frames at once. It reports rather than hides:

- garbage/desynchronization before magic bytes;
- unsupported/invalid headers;
- bad CRC or malformed complete frames;
- bounded-buffer overflow.

It may resynchronize to a later valid frame, but every discarded/corrupt segment is surfaced as a `StreamIssue`. `ProtocolTransport` raises those issues before returning a recovered frame, so corruption cannot silently disappear.

## Software-in-the-loop link

`SimulatedProtocolLink` gives tests connected host/device `ProtocolTransport` instances plus controlled raw-byte injection points. This lets later RobotGateway, heartbeat, watchdog, and replay tests use the same transport contract as physical hardware without claiming hardware validation.
