import Foundation

/// One person detection. Matches backend app/models.py Detection.
/// x, y are normalized image coords (0..1); the backend maps to grid cells.
struct Detection: Codable {
    let track_id: Int
    let x: Double
    let y: Double
    let t: Double                 // client epoch seconds
    let appearance_tags: [String] // e.g. ["赤い上着"] (color only for MVP)
}

/// Batch posted to `POST /ingest`. Matches backend IngestBatch.
struct IngestBatch: Codable {
    let camera_id: String
    let detections: [Detection]
}

/// One live session row from `GET /sessions`. Matches the backend read model:
/// the backend turns raw detections into grid position, dwell, shelf adjacency,
/// and (later) preference profile. Used by the operator dashboard screen.
struct SessionRow: Codable, Identifiable {
    let session_id: String
    let x: Int
    let y: Int
    let state: String
    let dwell_sec: Int
    let shelf_id: String?
    let elapsed_sec: Int
    let appearance_tags: [String]
    let profile: SessionProfile?

    var id: String { session_id }
}

/// Inferred taste preference for a session (backend `profile`).
/// Present once the backend has enough dwell/shelf signal.
struct SessionProfile: Codable {
    let tags: [String]
    let confidence: String
    let basis: [String]
}
