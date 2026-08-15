import Foundation

/// Posts detections to the KUMU backend. Data flow is spec-mandated:
/// iOS -> cloud -> PC (no device-to-device on the venue Wi-Fi).
final class APIClient {
    private let baseURL: URL
    private let session = URLSession(configuration: .default)

    init(baseURL: URL) { self.baseURL = baseURL }

    /// POST /ingest . Batches are small (one frame's detections).
    func postIngest(_ batch: IngestBatch) async {
        let url = baseURL.appendingPathComponent("/ingest")
        var req = URLRequest(url: url)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try? JSONEncoder().encode(batch)
        do {
            _ = try await session.data(for: req)
        } catch {
            print("ingest post failed: \(error)")
        }
    }

    /// GET /sessions?mock=true . Backend-derived live sessions for the operator
    /// dashboard (grid position, dwell, appearance). `mock=true` returns demo
    /// rows so the screen is populated without a live camera feed.
    func getSessions(mock: Bool = true) async -> [SessionRow] {
        var comps = URLComponents(url: baseURL.appendingPathComponent("/sessions"),
                                  resolvingAgainstBaseURL: false)
        if mock { comps?.queryItems = [URLQueryItem(name: "mock", value: "true")] }
        guard let url = comps?.url else { return [] }
        do {
            let (data, _) = try await session.data(from: url)
            return try JSONDecoder().decode([SessionRow].self, from: data)
        } catch {
            print("sessions fetch failed: \(error)")
            return []
        }
    }
}
