# KUMU iOS トラッカー（KumuTracker）

SwiftUI + Vision。iPhone を店内固定カメラにして、人を端末内検出し **足元の正規化
座標＋服装色タグ** をバックエンド `POST /ingest` へ送る。**生映像は送らない**
（プライバシー・帯域）。通信は spec 通り iOS → クラウド → PC の一方向。

## ソース構成
```
KumuTracker/
  KumuTrackerApp.swift          # @main
  Models/IngestModels.swift     # Detection / IngestBatch（backend と同形）
  Networking/APIClient.swift    # POST /ingest
  Tracking/CameraSession.swift  # AVCaptureSession フレーム供給
  Tracking/PersonTracker.swift  # Vision 人検出 -> 足元座標 + trackId
  Tracking/AppearanceColor.swift# 上半身の代表色 -> 日本語色ラベル（色のみMVP）
  Views/ContentView.swift       # 計測開始/停止
  Views/TrackingViewModel.swift # camera -> tracker -> api の結線
```

## Xcode プロジェクト作成（本 scaffold はソースのみ）
1. Xcode → New → App → SwiftUI、名前 `KumuTracker`
2. 生成された App/ContentView を削除し、`KumuTracker/` 配下を target に追加
3. Info.plist に **NSCameraUsageDescription**（例「店内トラッキングにカメラを使用します」）
4. `TrackingViewModel.swift` の `baseURL` を LAN 上の backend に（例 `http://192.168.0.10:8000`）
5. **実機で実行**（Simulator はカメラ無し）

## 次フェーズ（本 scaffold 対象外）
- ライブプレビュー（`AVCaptureVideoPreviewLayer`）＋検出足元のオーバーレイ
- body pose（`VNDetectHumanBodyPoseRequest`）での足元精度向上
- 店の床平面への homography 校正（4点対応）を端末 or サーバーで
