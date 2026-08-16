import Foundation

/// Result of trying to deliver ingest data, so the UI can show connection state.
struct IngestOutcome {
    let online: Bool        // was the backend reachable on this attempt?
    let buffered: Int       // batches still waiting to be delivered
    let delivered: Int      // batches flushed on this attempt (incl. retries)
}

/// Posts detections to the KUMU backend. Data flow is spec-mandated:
/// iOS -> cloud -> PC (no device-to-device on the venue Wi-Fi).
///
/// Resilience (B2): actor-isolated so buffer access is race-free. Each send
/// retries transient failures with backoff, and on failure the batch is kept in
/// a bounded FIFO buffer that is flushed automatically once the backend is
/// reachable again (reconnect). The server host can be changed at runtime so a
/// real device can point at the venue PC's LAN address.
actor APIClient {
    private var baseURL: URL
    private let session: URLSession

    // Offline buffer: bounded so a long outage can't grow memory without limit.
    private var buffer: [IngestBatch] = []
    private let maxBuffered: Int
    private let maxRetries: Int

    init(baseURL: URL, maxBuffered: Int = 120, maxRetries: Int = 2) {
        self.baseURL = baseURL
        self.maxBuffered = maxBuffered
        self.maxRetries = maxRetries
        let cfg = URLSessionConfiguration.default
        cfg.timeoutIntervalForRequest = 8
        cfg.waitsForConnectivity = false   // fail fast; we buffer + retry ourselves
        self.session = URLSession(configuration: cfg)
    }

    /// Point the client at a different backend (e.g. the venue PC's LAN IP).
    func setBaseURL(_ url: URL) { baseURL = url }

    var bufferedCount: Int { buffer.count }

    /// Enqueue a batch and try to deliver everything pending (oldest first).
    /// Returns the resulting connection state for the UI.
    func send(_ batch: IngestBatch) async -> IngestOutcome {
        buffer.append(batch)
        if buffer.count > maxBuffered {
            buffer.removeFirst(buffer.count - maxBuffered)   // drop stalest
        }
        var delivered = 0
        while let next = buffer.first {
            if await postOnce(next) {
                buffer.removeFirst()
                delivered += 1
            } else {
                return IngestOutcome(online: false, buffered: buffer.count, delivered: delivered)
            }
        }
        return IngestOutcome(online: true, buffered: 0, delivered: delivered)
    }

    /// GET /sessions . `mock=true` returns backend demo rows.
    func getSessions(mock: Bool) async -> [SessionRow] {
        var comps = URLComponents(url: baseURL.appendingPathComponent("/sessions"),
                                  resolvingAgainstBaseURL: false)
        if mock { comps?.queryItems = [URLQueryItem(name: "mock", value: "true")] }
        guard let url = comps?.url else { return [] }
        do {
            let (data, resp) = try await session.data(from: url)
            guard Self.isOK(resp) else { return [] }
            return try JSONDecoder().decode([SessionRow].self, from: data)
        } catch {
            return []
        }
    }

    // MARK: - Private

    private func postOnce(_ batch: IngestBatch) async -> Bool {
        guard let body = try? JSONEncoder().encode(batch) else { return true } // undecodable: drop
        let url = baseURL.appendingPathComponent("/ingest")
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = body

        for attempt in 0...maxRetries {
            do {
                let (_, resp) = try await session.data(for: req)
                if Self.isOK(resp) { return true }
            } catch {
                // network error -> fall through to backoff/retry
            }
            if attempt < maxRetries {
                try? await Task.sleep(nanoseconds: Self.backoff(attempt))
            }
        }
        return false
    }

    private static func isOK(_ resp: URLResponse) -> Bool {
        guard let http = resp as? HTTPURLResponse else { return false }
        return (200..<300).contains(http.statusCode)
    }

    /// Exponential-ish backoff: 200ms, 400ms, ...
    private static func backoff(_ attempt: Int) -> UInt64 {
        UInt64((200 * (1 << attempt)) * 1_000_000)
    }
}
