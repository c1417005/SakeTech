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
            await api.postIngest(batch)
            await MainActor.run { self.lastCount = detections.count }
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
