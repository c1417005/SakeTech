import SwiftUI

/// KUMU iOS tracker. Turns an iPhone into a fixed store camera: detects people
/// on-device (Vision), estimates a foot coordinate + clothing color, and streams
/// them to the KUMU backend `POST /ingest`. No raw video leaves the device.
@main
struct KumuTrackerApp: App {
    var body: some Scene {
        WindowGroup { ContentView() }
    }
}
