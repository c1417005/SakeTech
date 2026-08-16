# KUMU バックエンド設計

データフロー（PRD §9）: `iOS カメラ → クラウドサーバー（滞留記録・好み推定）→
GET /sessions → 店員Web`。推定はサーバー側。フロントは表示に専念。

```
iOS(Vision) --POST /ingest--> [backend] --GET /sessions--> 店員Web
                                 |  facing隣接判定 -> shelf_id
                                 |  滞留(dwell) -> state (moving/viewing/hesitating)
                                 |  dwell加重平均 -> profile(tags/confidence/basis)
                                 +-- さけのわ取得/キャッシュ -> /brands
```

## モジュール構成（`backend/app/`）
| file | 役割 |
|---|---|
| `main.py` | FastAPI 起動・CORS・DB init |
| `routes.py` | 全エンドポイント |
| `models.py` | Pydantic 型（API契約） |
| `db.py` | SQLite（マップ1件＋銘柄キャッシュ）。session は永続化しない |
| `geometry.py` | 棚占有・**facing 隣接判定**・画像→グリッド homography（任意） |
| `sessions.py` | live `SessionStore`（ingest駆動）＋ `DemoSimulator`（mock再生） |
| `inference.py` | 好み推定（dwell加重平均→タグ/確信度/根拠） |
| `sakenowa.py` | さけのわ取得・石川抽出・type4導出・平易語タグ |
| `seed_demo.py` | 実銘柄で架空店（棚4）＋デモ台本を seed |
| `config.py` | しきい値等（TBD 暫定値の一元管理） |

## facing 隣接判定（`shelf_id` はバックエンドの責務）
棚の**向いている側の隣接セルのみ**を判定範囲にする（4近傍ではない）。
- north/south → 棚は x 方向に伸長、front は y∓1
- east/west → 棚は y 方向に伸長、front は x±1
背中合わせ・壁際でも正しく分離できる。通路両側の向かい合わせは現状**最近1つ**を返す
（[TBD] 配列で返すか要合意）。

## state 判定（滞留秒）
`shelf_id==null → moving` / `dwell>=VIEWING_SEC → viewing` / `dwell>=HESITATING_SEC → hesitating`。

## 好み推定（`inference.py`）
1. 各棚前の滞留秒を、その棚の `brand_ids` に加算（`dwell_by_brand`）
2. flavor データのある銘柄で **滞留加重平均**の6軸ベクトルを算出
3. 中立(0.5)からの乖離が大きい軸を平易語タグ化（辛口寄り/甘口寄り/香り高い/コクがある/すっきり軽快/芳醇）、最大3
4. `confidence` は 根拠銘柄数 × 総滞留秒で low/medium/high。low は「推定中」
5. `basis` は長く見た銘柄名 最大3

## type4 導出（さけのわ6軸から）
香り(f1 華やか) × 濃淡(f3 重厚) の2軸:
薫酒=香高・淡麗 / 爽酒=香低・淡麗 / 醇酒=香低・濃醇 / 熟酒=香高・濃醇。
別入力せず数値から導出（PRD §9 と一致）。欠損銘柄は導出しない=銘柄名のみ。

## デモ / モック再生（当日の本番経路）
`DemoSimulator` が「入店→1〜3番棚を回遊→4番で迷う」を**閉形式**で再生。経過秒から
状態を決めるので毎ポーリング冪等・ドリフトしない。`GET /sessions?mock=true`
（または `KUMU_MOCK=true`）で有効。**実 ingest と同じ推定パイプラインを通す**ので
デモの数値も本物と同じロジック由来。

デモ銘柄（さけのわ実データで検証済・flavor有）:
手取川(470) / 福正宗(488) / 天狗舞(469) / 菊姫(1041)。石川=濃厚芳醇=醇酒寄りの筋書き。

## TBD（暫定値と根拠・要人間合意）
`config.py` に集約。フロント側 PRD の TBD と対応。

| 項目 | 暫定値 | 根拠 |
|---|---|---|
| 迷い判定しきい値 `HESITATING_SEC` | 20s | 「見た(4s)」より明確に長い。デモの4番棚(25s)で確実に発火 |
| 見ている `VIEWING_SEC` | 4s | 通過(数百ms)と区別できる最小 |
| グリッド粒度 | 10×8 固定 | map-spec の決定事項 |
| 服装タグ項目 | 色のみ（上着色）| 顧客識別doc「MVPは色のみ」。持ち物は後 |
| profile 根拠最小滞留 `BASIS_MIN_DWELL_SEC` | 5s | 通りすがりを根拠に入れない |
| 確信度 high | 根拠3銘柄 かつ 総滞留30s | 断定を鵜呑みさせない安全側 |
| type4 しきい値 | 香り0.30 / 濃淡0.40 | さけのわ f 値分布（0.1〜0.6中心）に合わせた暫定。要チューニング |
| 向かい合う棚 | 最近1つ | map-spec の未決事項。配列化は要合意 |
| ingest→グリッド写像 | 正規化×グリッド寸法 | 校正UI未実装のため暫定。homography に差し替え予定 |

## 個人情報 / ライセンス
顔特徴量は保存しない・識別しない・session は退店で消滅（メモリのみ）。
さけのわ帰属表示は `/attribution` で供給（画面常設が利用規約上必須）。
