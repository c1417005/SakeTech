import Foundation
import Vision
import CoreVideo

/// On-device person detection + naive tracking + clothing-color appearance.
///
/// - Vision `VNDetectHumanRectanglesRequest` finds people.
/// - Foot point = bottom-center of the bbox (ground contact), normalized 0..1,
///   top-left origin (backend convention).
/// - A greedy nearest-neighbour matcher keeps trackIds stable across frames.
/// - Appearance = dominant color sampled from the upper-body region, mapped to
///   a Japanese color label (MVP: color only, per PRD TBD).
///
/// The backend does grid mapping, shelf adjacency, dwell, and preference
/// inference. This class only emits `[Detection]` per frame.
final class PersonTracker {

    private struct Tracked { var id: Int; var x: Double; var y: Double }
    private var tracked: [Tracked] = []
    private var nextId = 1
    private let matchThreshold = 0.08

    private let request = VNDetectHumanRectanglesRequest()

    func process(pixelBuffer: CVPixelBuffer, timestamp: Double) -> [Detection] {
        let handler = VNImageRequestHandler(cvPixelBuffer: pixelBuffer, orientation: .up)
        try? handler.perform([request])
        let observations = request.results ?? []

        var out: [Detection] = []
        var used = Set<Int>()

        for obs in observations {
            let bb = obs.boundingBox              // Vision: bottom-left origin
            let fx = Double(bb.midX)
            let fy = Double(1.0 - bb.minY)        // feet -> top-left origin
            let id = assignId(fx: fx, fy: fy, used: &used)
            let color = AppearanceColor.dominantUpperBody(pixelBuffer: pixelBuffer, boundingBox: bb)
            let tags = color.map { ["\($0)の服"] } ?? []
            out.append(Detection(track_id: id, x: fx, y: fy, t: timestamp, appearance_tags: tags))
        }
        return out
    }

    private func assignId(fx: Double, fy: Double, used: inout Set<Int>) -> Int {
        var bestIdx = -1
        var bestDist = matchThreshold
        for (i, t) in tracked.enumerated() where !used.contains(i) {
            let d = hypot(t.x - fx, t.y - fy)
            if d < bestDist { bestDist = d; bestIdx = i }
        }
        if bestIdx >= 0 {
            tracked[bestIdx].x = fx; tracked[bestIdx].y = fy
            used.insert(bestIdx)
            return tracked[bestIdx].id
        }
        let id = nextId; nextId += 1
        tracked.append(Tracked(id: id, x: fx, y: fy))
        used.insert(tracked.count - 1)
        return id
    }
}
