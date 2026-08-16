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

            HStack {
                Text("サーバ")
                TextField("127.0.0.1:8000", text: $vm.serverHost)
                    .textFieldStyle(.roundedBorder)
                    .autocorrectionDisabled()
                    .textInputAutocapitalization(.never)
                    .frame(width: 180)
                Button("適用") { vm.applyServerHost() }
                    .buttonStyle(.bordered)
            }

            // Connection health (B2): online / buffering while disconnected.
            HStack(spacing: 6) {
                Image(systemName: vm.connectionOnline
                      ? "wifi" : "wifi.exclamationmark")
                Text(vm.connectionOnline
                     ? "接続OK"
                     : "再接続待ち・未送信 \(vm.bufferedCount) 件をバッファ中")
            }
            .font(.footnote)
            .foregroundStyle(vm.connectionOnline ? .green : .orange)

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
                    List {
                        Section {
                            SessionSummaryBar(sessions: vm.sessions)
                                .listRowInsets(EdgeInsets())
                                .listRowBackground(Color.clear)
                        }
                        Section {
                            ForEach(vm.sessions) { s in SessionRowView(session: s) }
                        }
                    }
                    .listStyle(.insetGrouped)
                }
            }
            .navigationTitle("セッション")
            .safeAreaInset(edge: .top) {
                VStack(spacing: 6) {
                    Picker("データ源", selection: Binding(
                        get: { vm.liveMode },
                        set: { vm.setLiveMode($0) }
                    )) {
                        Text("ライブ").tag(true)
                        Text("デモ").tag(false)
                    }
                    .pickerStyle(.segmented)

                    if vm.liveMode && !vm.connectionOnline {
                        Label("再接続待ち・未送信 \(vm.bufferedCount) 件をバッファ中",
                              systemImage: "wifi.exclamationmark")
                            .font(.caption).foregroundStyle(.orange)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    }
                }
                .padding(.horizontal)
                .padding(.vertical, 6)
                .background(.bar)
            }
            .toolbar {
                ToolbarItem(placement: .principal) {
                    if vm.liveMode && vm.isPollingSessions {
                        HStack(spacing: 5) {
                            Circle().fill(.green).frame(width: 8, height: 8)
                            Text("ライブ").font(.caption).foregroundStyle(.secondary)
                        }
                    }
                }
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

// MARK: - Dashboard building blocks (B3)

/// Visual identity for the three backend session states, so operators can read
/// the room at a glance (moving/viewing/hesitating). Mirrors backend SessionState.
enum SessionStateStyle {
    static func color(_ state: String) -> Color {
        switch state {
        case "hesitating": return .orange   // 迷っている = 声かけ好機
        case "viewing":    return .green     // 見ている
        default:            return .blue      // moving / unknown
        }
    }

    static func label(_ state: String) -> String {
        switch state {
        case "hesitating": return "迷っている"
        case "viewing":    return "見ている"
        case "moving":     return "移動中"
        default:            return state
        }
    }

    static func icon(_ state: String) -> String {
        switch state {
        case "hesitating": return "hand.raised.fill"
        case "viewing":    return "eye.fill"
        default:            return "figure.walk"
        }
    }
}

/// Count-by-state summary shown above the live session list.
struct SessionSummaryBar: View {
    let sessions: [SessionRow]

    private func count(_ state: String) -> Int {
        sessions.filter { $0.state == state }.count
    }

    var body: some View {
        HStack(spacing: 10) {
            stat("合計", sessions.count, .primary)
            Divider().frame(height: 28)
            stat(SessionStateStyle.label("viewing"), count("viewing"),
                 SessionStateStyle.color("viewing"))
            stat(SessionStateStyle.label("hesitating"), count("hesitating"),
                 SessionStateStyle.color("hesitating"))
            stat(SessionStateStyle.label("moving"), count("moving"),
                 SessionStateStyle.color("moving"))
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
    }

    private func stat(_ title: String, _ value: Int, _ color: Color) -> some View {
        VStack(spacing: 2) {
            Text("\(value)").font(.title3).bold().foregroundStyle(color)
            Text(title).font(.caption2).foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity)
    }
}

/// One live session row with a state-colored pill and key metrics.
struct SessionRowView: View {
    let session: SessionRow

    var body: some View {
        let color = SessionStateStyle.color(session.state)
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Text(session.session_id).font(.headline).lineLimit(1)
                Spacer()
                Label(SessionStateStyle.label(session.state),
                      systemImage: SessionStateStyle.icon(session.state))
                    .font(.caption).bold()
                    .padding(.horizontal, 8).padding(.vertical, 3)
                    .background(color.opacity(0.18))
                    .foregroundStyle(color)
                    .clipShape(Capsule())
            }
            Text("位置 (\(session.x), \(session.y))・滞在 \(session.dwell_sec)s・経過 \(session.elapsed_sec)s")
                .font(.subheadline).foregroundStyle(.secondary)
            if let shelf = session.shelf_id {
                Label("棚: \(shelf)", systemImage: "books.vertical").font(.caption)
            }
            if !session.appearance_tags.isEmpty {
                Text(session.appearance_tags.joined(separator: "・"))
                    .font(.caption).foregroundStyle(.secondary)
            }
            if let p = session.profile {
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

#Preview { ContentView() }
