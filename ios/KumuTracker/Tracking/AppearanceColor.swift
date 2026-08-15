import CoreVideo
import CoreImage

/// Samples the dominant color of a person's upper body and maps it to a
/// Japanese color label. MVP appearance = clothing color only (PRD TBD).
///
/// No image is stored or transmitted; only the resulting label leaves the device.
enum AppearanceColor {

    private static let context = CIContext(options: [.workingColorSpace: NSNull()])

    /// Returns a color label like "赤" / "青" / "黒", or nil if it can't sample.
    static func dominantUpperBody(pixelBuffer: CVPixelBuffer, boundingBox: CGRect) -> String? {
        let ci = CIImage(cvPixelBuffer: pixelBuffer)
        let w = ci.extent.width, h = ci.extent.height

        // Vision bbox is normalized, bottom-left origin. Upper body = top ~30%.
        let region = CGRect(
            x: boundingBox.minX * w,
            y: (boundingBox.maxY - boundingBox.height * 0.35) * h,
            width: boundingBox.width * w,
            height: boundingBox.height * 0.30 * h
        ).intersection(ci.extent)
        guard !region.isNull, region.width >= 1, region.height >= 1 else { return nil }

        // Average color via CIAreaAverage.
        guard let filter = CIFilter(name: "CIAreaAverage", parameters: [
            kCIInputImageKey: ci,
            kCIInputExtentKey: CIVector(cgRect: region),
        ]), let output = filter.outputImage else { return nil }

        var px = [UInt8](repeating: 0, count: 4)
        context.render(output, toBitmap: &px, rowBytes: 4, bounds: CGRect(x: 0, y: 0, width: 1, height: 1),
                       format: .RGBA8, colorSpace: nil)
        return label(r: px[0], g: px[1], b: px[2])
    }

    /// Coarse RGB -> Japanese color name.
    static func label(r: UInt8, g: UInt8, b: UInt8) -> String {
        let rf = Double(r), gf = Double(g), bf = Double(b)
        let maxV = max(rf, gf, bf), minV = min(rf, gf, bf)
        if maxV < 60 { return "黒" }
        if minV > 190 { return "白" }
        if maxV - minV < 40 { return "灰" }
        if rf >= gf && rf >= bf { return gf > 120 ? "黄" : "赤" }
        if gf >= rf && gf >= bf { return "緑" }
        return "青"
    }
}
