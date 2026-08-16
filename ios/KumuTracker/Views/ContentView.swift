import SwiftUI

/// Operator surface. Tab 1 = the tracker controls (camera id, start/stop).
/// Tab 2 = the backend session dashboard (GET /sessions), so demo data is
/// visible even in the Simulator where there is no camera.
struct ContentView: View {
    @StateObject private var vm = TrackingViewModel()

    var body: some View {
        TabView(selection: $vm.selectedTab) {
            TrackerView(vm: vm)
                .tabItem { Label("トラッカー", systemImage: "camera.viewfinder") }
                .tag(0)
            SessionsView(vm: vm)
                .tabItem { Label("セッション", systemImage: "list.bullet.rectangle") }
                .tag(1)
        }
    }
}

/// Minimal tracker control surface: set camera id, start/stop measuring.
struct TrackerView: View {
    @ObservedObject var vm: TrackingViewModel

    var body: some View {
        VStack(spacing: 20) {
            Text("KUMU トラッカー").font(.largeTitle).bold()

            HStack {
                Text("カメラID")
                TextField("cam-1", text: $vm.cameraId)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 120)
            }

            Text(vm.isRunning ? "計測中… 検出人数: \(vm.lastCount)" : "停止中")
                .foregroundStyle(vm.isRunning ? .green : .secondary)

            Button(vm.isRunning ? "停止" : "計測開始") { vm.toggle() }
                .buttonStyle(.borderedProminent)

            if vm.isSimulator {
                Text("Simulator ではカメラが無いため、疑似検出データを /ingest に送信します（実カメラ検出は実機のみ）")
                    .font(.footnote).foregroundStyle(.orange)
                    .multilineTextAlignment(.center)
            }

            Text("映像は端末内で処理し、座標と服装タグのみ送信します")
                .font(.footnote).foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .padding()
    }
}

/// Backend session dashboard. Live by default (real /ingest-derived data, polled
/// every ~2s); a toggle switches to backend demo rows for a dry screen.
struct SessionsView: View {
    @ObservedObject var vm: TrackingViewModel

    var body: some View {
        NavigationStack {
            Group {
                if vm.sessions.isEmpty {
                    ContentUnavailableView {
                        Label("セッションなし", systemImage: "person.3")
                    } description: {
                        Text(vm.liveMode
                             ? "計測を開始すると、来店者が実データで表示されます"
                             : "「更新」でバックエンドのデモデータを取得します")
                    }
                } else {
                    List(vm.sessions) { s in
                        VStack(alignment: .leading, spacing: 6) {
                            HStack {
                                Text(s.session_id).font(.headline)
                                Spacer()
                                Text(s.state)
                                    .font(.caption).bold()
                                    .padding(.horizontal, 8).padding(.vertical, 2)
                                    .background(s.state == "moving" ? Color.blue.opacity(0.2)
                                                                     : Color.green.opacity(0.2))
                                    .clipShape(Capsule())
                            }
                            Text("位置 (\(s.x), \(s.y))・滞在 \(s.dwell_sec)s・経過 \(s.elapsed_sec)s")
                                .font(.subheadline).foregroundStyle(.secondary)
                            if let shelf = s.shelf_id {
                                Text("棚: \(shelf)").font(.caption)
                            }
                            if !s.appearance_tags.isEmpty {
                                Text(s.appearance_tags.joined(separator: "・"))
                                    .font(.caption).foregroundStyle(.secondary)
                            }
                            if let p = s.profile {
                                HStack(spacing: 6) {
                                    Image(systemName: "sparkles")
                                    Text("嗜好: \(p.tags.joined(separator: "・")) (\(p.confidence))")
                                }
                                .font(.caption).foregroundStyle(.purple)
                            }
                        }
                        .padding(.vertical, 4)
                    }
                }
            }
            .navigationTitle("セッション")
            .safeAreaInset(edge: .top) {
                Picker("データ源", selection: Binding(
                    get: { vm.liveMode },
                    set: { vm.setLiveMode($0) }
                )) {
                    Text("ライブ").tag(true)
                    Text("デモ").tag(false)
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)
                .padding(.vertical, 6)
                .background(.bar)
            }
            .toolbar {
                ToolbarItem(placement: .primaryAction) {
                    Button("更新") { vm.refreshSessions() }
                }
            }
            // Live: poll while visible so state changes appear in near real time.
            .onAppear { vm.startSessionsPolling() }
            .onDisappear { vm.stopSessionsPolling() }
        }
    }
}

#Preview { ContentView() }
