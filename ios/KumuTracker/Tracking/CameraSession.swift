import AVFoundation
import CoreVideo

/// Wraps AVCaptureSession and delivers frames. Requires NSCameraUsageDescription
/// and a real device (Simulator has no camera).
final class CameraSession: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {
    let session = AVCaptureSession()
    private let output = AVCaptureVideoDataOutput()
    private let queue = DispatchQueue(label: "kumu.camera.frames")

    var onFrame: ((CVPixelBuffer, Double) -> Void)?

    func configure() {
        session.beginConfiguration()
        session.sessionPreset = .high
        if let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .back),
           let input = try? AVCaptureDeviceInput(device: device),
           session.canAddInput(input) {
            session.addInput(input)
        }
        output.setSampleBufferDelegate(self, queue: queue)
        output.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String:
                                    Int(kCVPixelFormatType_32BGRA)]
        if session.canAddOutput(output) { session.addOutput(output) }
        session.commitConfiguration()
    }

    func start() { if !session.isRunning { session.startRunning() } }
    func stop() { if session.isRunning { session.stopRunning() } }

    func captureOutput(_ output: AVCaptureOutput,
                       didOutput sampleBuffer: CMSampleBuffer,
                       from connection: AVCaptureConnection) {
        guard let pb = CMSampleBufferGetImageBuffer(sampleBuffer) else { return }
        onFrame?(pb, Date().timeIntervalSince1970)
    }
}
