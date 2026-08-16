import Foundation
import Combine

/// Glues CameraSession -> PersonTracker -> APIClient (POST /ingest), and also
/// loads the backend session dashboard (GET /sessions).
///
/// On a real device the camera drives detections. In the Simulator (no camera)
/// we fall back to a synthetic detection generator so the operator UI, counters,
/// and network path are all exercisable without hardware.
@MainActor
final class TrackingViewModel: ObservableObject {
    @Published var cameraId: String = "cam-1"
    @Published var isRunning = false
    @Published var lastCount = 0
    @Published var sessions: [SessionRow] = []
    @Published var isSimulator = false
    /// Ingest connection health (B2). `false` => posts are failing and being
    /// buffered for retry; `bufferedCount` is how many batches are waiting.
    @Published var connectionOnline = true
    @Published var bufferedCount = 0
    /// Backend host:port. Editable so a real device can reach the venue PC over
    /// LAN (the Simulator can use 127.0.0.1, a device cannot).
    @Published var serverHost = "127.0.0.1:8000"
    /// Dashboard data source. `true` (default) = live sessions derived from real
    /// /ingest data; `false` = backend demo rows (?mock=true) for a dry screen.
    @Published var liveMode = true
    /// True while the sessions dashboard is auto-refreshing.
    @Published var isPollingSessions = false
    /// Selected tab. Overridable at launch via env `KUMU_START=sessions`
    /// (useful for demos / screenshots without tapping).
    @Published var selectedTab = 0

    // KUMU backend. Localhost reaches the host machine from the iOS Simulator.
    private let api = APIClient(baseURL: URL(string: "http://127.0.0.1:8000")!)
    private let camera = CameraSession()
    private let tracker = PersonTracker()
    private var mockTimer: Timer?
    private var mockTick = 0
    private var sessionsTimer: Timer?
    /// How often the dashboard polls GET /sessions while visible.
    private let sessionsPollInterval: TimeInterval = 2.0

    init() {
        #if targetEnvironment(simulator)
        isSimulator = true
        #endif

        // Demo/screenshot override: KUMU_DEMO=1 shows backend mock rows.
        if ProcessInfo.processInfo.environment["KUMU_DEMO"] == "1" {
            liveMode = false
        }

        if ProcessInfo.processInfo.environment["KUMU_START"] == "sessions" {
            selectedTab = 1
            refreshSessions()
        }

        camera.onFrame = { [weak self] pixelBuffer, t in
            guard let self else { return }
            let detections = self.tracker.process(pixelBuffer: pixelBuffer, timestamp: t)
            self.send(detections)
        }
    }

    func toggle() {
        if isRunning {
            camera.stop()
            mockTimer?.invalidate(); mockTimer = nil
            isRunning = false
        } else {
            if isSimulator {
                startMockStream()
            } else {
                camera.configure(); camera.start()
            }
            isRunning = true
        }
    }

    /// Loads the session dashboard. Live by default (real /ingest-derived data);
    /// backend demo rows only when `liveMode` is off.
    func refreshSessions() {
        let wantMock = !liveMode
        Task {
            let rows = await api.getSessions(mock: wantMock)
            await MainActor.run { self.sessions = rows }
        }
    }

    /// Flip live vs demo and reload immediately.
    func setLiveMode(_ live: Bool) {
        guard live != liveMode else { return }
        liveMode = live
        refreshSessions()
    }

    /// Apply the edited backend host (e.g. "192.168.1.20:8000") to the client.
    func applyServerHost() {
        let trimmed = serverHost.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty, let url = URL(string: "http://\(trimmed)") else { return }
        Task { await api.setBaseURL(url) }
        refreshSessions()
    }

    /// Start polling GET /sessions so the dashboard reflects state changes
    /// (moving -> viewing -> hesitating) in near real time. Idempotent.
    func startSessionsPolling() {
        refreshSessions()
        guard sessionsTimer == nil else { return }
        isPollingSessions = true
        sessionsTimer = Timer.scheduledTimer(withTimeInterval: sessionsPollInterval,
                                             repeats: true) { [weak self] _ in
            Task { @MainActor in self?.refreshSessions() }
        }
    }

    func stopSessionsPolling() {
        sessionsTimer?.invalidate(); sessionsTimer = nil
        isPollingSessions = false
    }

    // MARK: - Private

    private func send(_ detections: [Detection]) {
        let batch = IngestBatch(camera_id: cameraId, detections: detections)
        Task {
            let outcome = await api.send(batch)
            await MainActor.run {
                self.lastCount = detections.count
                self.connectionOnline = outcome.online
                self.bufferedCount = outcome.buffered
            }
        }
    }

    /// Simulator-only: emit a couple of moving synthetic detections each second,
    /// so the counter updates and the backend actually receives /ingest posts.
    private func startMockStream() {
        mockTick = 0
        mockTimer = Timer.scheduledTimer(withTimeInterval: 1.0, repeats: true) { [weak self] _ in
            guard let self else { return }
            Task { @MainActor in
                self.mockTick += 1
                let phase = Double(self.mockTick)
                let colors = ["赤", "青", "黒", "白", "緑"]
                let people = (0..<2).map { i -> Detection in
                    let base = 0.3 + 0.2 * Double(i)
                    return Detection(
                        track_id: i + 1,
                        x: min(0.95, max(0.05, base + 0.15 * sin(phase / 3 + Double(i)))),
                        y: min(0.95, max(0.05, 0.5 + 0.2 * cos(phase / 4 + Double(i)))),
                        t: Date().timeIntervalSince1970,
                        appearance_tags: ["\(colors[(self.mockTick + i) % colors.count])の服"]
                    )
                }
                self.send(people)
            }
        }
    }
}
