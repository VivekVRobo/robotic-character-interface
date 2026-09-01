# Event System

The in-process event bus is a bounded asynchronous priority queue. Producers cannot create unbounded memory growth: normal `publish()` applies backpressure and `publish_nowait()` explicitly fails with `EventQueueFull` when capacity is exhausted.

Subscriptions are typed by event class. A subscriber to `Event` receives all subclasses; a subscriber to a concrete event receives only that event class and subclasses. Handler failures are isolated, counted, and retained in bounded failure history so one subscriber cannot prevent later subscribers from receiving the same event.

Events contain wall-clock timestamps for audit/history and monotonic timestamps for latency/freshness calculations. `interaction_id` will correlate complete multimodal flows across gesture, cognition, behavior, safety, and robotics.

The default bus uses one worker for deterministic ordering. Additional workers are supported only where ordering trade-offs are understood. Priority applies to events waiting in the queue; it does not preempt a handler already executing.
